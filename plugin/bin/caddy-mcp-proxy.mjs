#!/usr/bin/env node
// Caddy MCP stdio-to-HTTP/SSE proxy.
//
// Why this script exists: Claude Code plugin .mcp.json does not expand
// ${VAR} in `headers` field values (Issue anthropics/claude-code#9427,
// still active on v2.0.7x and v2.1.x). The env-block DOES expand. So
// the plugin declares an `env` block with the secrets, this script
// reads them at runtime, and posts to Caddy's /api/mcp endpoint with
// the proper Authorization header attached. Caddy's /api/mcp is
// bearer-only single-billing (no BYOK, no Anthropic call), so the
// bearer token is the only secret this proxy needs.
//
// Why not use a third-party tool: mcp-remote bakes OAuth discovery
// into every connect, which crashes against bearer-token-only servers.
// Caddy's /api/mcp uses simple bearer auth, not OAuth. A purpose-built
// 100-line proxy avoids that mismatch and has zero supply-chain dep.
//
// Logging discipline: stderr lines are visible to Claude Code's plugin
// debugging UI. NEVER log the bearer token, the request body, or
// response body. Only log error categories.

import { createInterface } from 'node:readline'
import { readFileSync, statSync } from 'node:fs'
import { homedir } from 'node:os'
import { join } from 'node:path'

// Resolve the bearer token. Primary source is the env block the plugin
// .mcp.json expands (CADDY_BEARER_TOKEN). Fallback: a token file, so the proxy
// also works when Claude Code is launched from the macOS Dock / Finder, where a
// GUI app does NOT inherit shell env from ~/.zshrc (only Terminal-launched
// sessions do). File path is CADDY_BEARER_TOKEN_FILE, else ~/.caddy/bearer-token.
// Logging discipline (see header): NEVER log the token; a loose-perms warning is fine.
function resolveBearer() {
  const fromEnv = process.env.CADDY_BEARER_TOKEN
  if (fromEnv && fromEnv.trim()) return fromEnv.trim()
  const file = process.env.CADDY_BEARER_TOKEN_FILE || join(homedir(), '.caddy', 'bearer-token')
  try {
    const token = readFileSync(file, 'utf8').trim()
    if (!token) return undefined
    try {
      // A bearer-token file should be user-only (0600). Warn (don't fail) if it
      // is group/other-accessible so the user can tighten it.
      if (statSync(file).mode & 0o077) {
        console.error(`CADDY_BEARER_TOKEN_FILE ${file} is group/other-accessible; run: chmod 600 ${file}`)
      }
    } catch {
      // stat failure is non-fatal; the token was already read.
    }
    return token
  } catch {
    // No file, unreadable, or empty — fall through to the not-set exit below.
    return undefined
  }
}

const BEARER = resolveBearer()
const URL = process.env.CADDY_MCP_URL || 'https://api.meetcaddy.com/api/mcp'

if (!BEARER) {
  console.error('CADDY_BEARER_TOKEN not set. Export it in the shell that launched Claude Code (then restart), or write it to ~/.caddy/bearer-token (chmod 600) so a Dock-launched app can read it. See plugin/README.md for the bearer-token issuance flow.')
  process.exit(1)
}

const HEADERS = {
  'Authorization': `Bearer ${BEARER}`,
  'Content-Type': 'application/json',
  'Accept': 'application/json, text/event-stream',
}

const writeLine = (s) => process.stdout.write(s + '\n')

const errorResponse = (id, message) =>
  JSON.stringify({
    jsonrpc: '2.0',
    id: id ?? null,
    error: { code: -32603, message: `proxy: ${message}` },
  })

async function forwardRequest(line) {
  let requestId = null
  try {
    requestId = JSON.parse(line)?.id ?? null
  } catch {
    // Non-JSON line on stdin; ignore (Claude Code shouldn't send these)
    return
  }

  let resp
  try {
    resp = await fetch(URL, {
      method: 'POST',
      headers: HEADERS,
      body: line,
    })
  } catch (err) {
    // Network / DNS / TLS failure — fetch couldn't reach Caddy at all.
    // Wrap as JSON-RPC error so Claude Code renders something readable
    // instead of a silent timeout. Cause code is more informative than
    // the generic TypeError name fetch throws on unroutable hosts.
    const code = err.cause?.code || err.code || err.name || 'fetch failed'
    writeLine(errorResponse(requestId, `could not reach Caddy server (${code})`))
    return
  }

  if (!resp.ok) {
    // Any non-2xx response from /api/mcp is an auth or server error, NOT a
    // valid MCP protocol response. Wrap in a JSON-RPC error envelope so
    // Claude Code surfaces it cleanly rather than parsing a raw HTTP body
    // as if it were MCP. Truncate the upstream body to avoid leaking
    // anything large into stdout/transcripts.
    let upstreamBody = ''
    try {
      const body = await resp.text()
      upstreamBody = body.length > 160 ? body.slice(0, 160) + '...' : body
    } catch {
      // ignore body read failure; status code alone is enough
    }
    const suffix = upstreamBody ? `: ${upstreamBody}` : ''
    writeLine(errorResponse(requestId, `upstream ${resp.status}${suffix}`))
    return
  }

  const contentType = resp.headers.get('content-type') || ''

  if (contentType.includes('text/event-stream')) {
    // SSE: parse `data:` lines, forward each as a stdout line.
    // Each SSE event contains one JSON-RPC message (response OR notification).
    const reader = resp.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''
    try {
      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })
        // Events are separated by blank lines (\n\n)
        const events = buffer.split('\n\n')
        buffer = events.pop() ?? ''
        for (const event of events) {
          for (const eventLine of event.split('\n')) {
            if (eventLine.startsWith('data: ')) {
              writeLine(eventLine.slice(6))
            } else if (eventLine.startsWith('data:')) {
              writeLine(eventLine.slice(5))
            }
            // Skip `event:`, `id:`, comments (`:`), and heartbeats
          }
        }
      }
      // Flush trailing buffer if it contains a data line
      for (const eventLine of buffer.split('\n')) {
        if (eventLine.startsWith('data: ')) {
          writeLine(eventLine.slice(6))
        } else if (eventLine.startsWith('data:')) {
          writeLine(eventLine.slice(5))
        }
      }
    } catch (err) {
      writeLine(errorResponse(requestId, `stream interrupted: ${err.code || err.name || 'read error'}`))
    }
  } else {
    // JSON: forward the response body as-is
    try {
      const body = await resp.text()
      writeLine(body)
    } catch (err) {
      writeLine(errorResponse(requestId, `body read failed: ${err.code || err.name || 'read error'}`))
    }
  }
}

// Track in-flight requests so we don't exit on stdin EOF mid-response
const pending = new Set()

const rl = createInterface({ input: process.stdin, crlfDelay: Infinity })

rl.on('line', (line) => {
  if (!line.trim()) return
  // Don't await here so subsequent stdin lines can be read while a request
  // is in flight. Track the promise so close-handling can drain it.
  const p = forwardRequest(line).finally(() => pending.delete(p))
  pending.add(p)
})

rl.on('close', async () => {
  // Drain in-flight requests before exiting so stdin EOF doesn't kill
  // an in-progress streaming response. Claude Code closes stdin when it
  // shuts down the MCP server; we want every reply to land before exit.
  if (pending.size > 0) {
    await Promise.allSettled([...pending])
  }
  process.exit(0)
})

// Graceful signal handling so Claude Code can cleanly stop the proxy
process.on('SIGINT', () => process.exit(0))
process.on('SIGTERM', () => process.exit(0))
