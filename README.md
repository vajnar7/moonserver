# moonserver
Server for Moonstalker project.

## Flask State Machine Service

This project provides a simple Flask REST API around a state machine with the following states:
- `ready`
- `connecting`
- `connected`
- `error`

The app exposes commands for connecting, reporting I/O responses, checking state, and resetting.

## Setup

Install dependencies:

```bash
pip install -r requirements.txt
```

Run the server:

```bash
python app.py
```

## Endpoints

### `POST /command/connect`
Start a connect command.

Response example:

```json
{
  "success": true,
  "message": "Connection attempt started.",
  "state": "connecting",
  "error_data": null
}
```

### `POST /command/connect/response`
Report an I/O response from an external component.

Request example:

```json
{
  "success": true
}
```

If the response indicates failure:

```json
{
  "success": false,
  "message": "Connection failed: example reason"
}
```

### `GET /state`
Read the current machine state and any error data.

### `POST /command/reset`
Reset the machine back to `ready`.

## Behavior

When `/command/connect` is received, the machine moves to `connecting` and starts a 3-second timeout.
If no I/O response is received in that window, the machine transitions to `error` with:

```json
{
  "state": "error",
  "error_data": "Connection failed: no response from I/O"
}
```

This flow is designed for frontend clients such as Android applications to trigger connect and then poll or receive state updates.
