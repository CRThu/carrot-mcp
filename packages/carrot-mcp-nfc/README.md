# carrot-mcp-nfc

Carrot MCP NFC Server — wraps [nfcscript](https://github.com/CRThu/nfcscript) for NFC reader communication via MCP.

## Tools

| Tool | Description |
|------|-------------|
| `version` | Get server version info |
| `list_readers` | List available reader types and transports |
| `connect` | Connect to NFC reader (port, reader_type, transport) |
| `disconnect` | Disconnect from reader |
| `find` | Find and activate an NFC card (returns uid, atq, sak) |
| `transceive` | Raw frame exchange with bit-level control (InCommunicateThru) |
| `reqa` | ISO14443-A REQA (7-bit short frame) |
| `wupa` | ISO14443-A WUPA (7-bit short frame) |
| `halt` | ISO14443-A HALT |
| `select` | ISO14443-A SELECT |
| `anticoll` | ISO14443-A ANTICOLL (anti-collision) |
| `field_on` / `field_off` | Control RF field |
| `script` | Execute a sequence of NFC operations (see below) |
| `trace_get` | Get trace log entries (supports level/layer filtering) |
| `trace_clear` | Clear trace log buffer |

## Supported Readers

- `pn532` — PN532 HSU (default)
- `clrc663` — CLRC663 UART

Use `list_readers` to see all registered types at runtime.

## Supported Transports

- `serial` — Serial/UART (default)

Use `list_readers` to see all registered types at runtime.

## Usage

```bash
uv run carrot-mcp nfc
```

## Script Tool

`script` executes a sequence of NFC operations. Each step is a dict with an `op` field:

| Op | Params | Description |
|----|--------|-------------|
| `transceive` | `data` (hex), `tx_crc`?, `rx_crc`?, `last_tx_bits`? | Raw frame exchange |
| `find` | `low_level`? (bool) | Find and activate card |
| `reqa` | — | REQA (7-bit short frame) |
| `wupa` | — | WUPA (7-bit short frame) |
| `halt` | — | HALT command |
| `select` | `cl_level` (int), `uid` (hex) | SELECT command |
| `anticoll` | `cl_level`?, `nvb`?, `uid_prefix`? (hex) | Anti-collision |
| `field_on` | — | Turn on RF field |
| `field_off` | — | Turn off RF field |
| `wait` | `ms` (int) | Wait for N milliseconds |

### Expect Matching

Data ops (`transceive`, `find`, `reqa`, `wupa`, `select`, `anticoll`) support `expect`, `expect_bits`, and `on_mismatch`:

```json
[
  {"op": "transceive", "data": "26", "last_tx_bits": 7, "expect": "0A", "expect_bits": 4, "on_mismatch": "stop"}
]
```

- `expect` (hex): Expected response data for matching (case-insensitive).
- `expect_bits`: Number of valid bits in the last byte (1-8). Only the lower N bits of the last byte are compared; upper bits are treated as 0. Useful for 4-bit ACK/NAK responses.
- `on_mismatch`: `"stop"` (default) aborts the script on mismatch; `"continue"` logs the mismatch but proceeds.

The script stops on the first error or `on_mismatch: "stop"`.

## Example MCP Call Sequence

```
list_readers()
connect(port="COM20", reader_type="pn532")
find()
transceive(data="6007", last_tx_bits=7, tx_crc=false, rx_crc=false)
reqa()
wupa()
select(cl_level=1, uid="04AABBCCDD77")
anticoll(cl_level=1)
halt()
field_off()
trace_get()
trace_clear()
disconnect()
```
