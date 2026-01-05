**API will be available at**:
   - API: http://localhost:8000
   - Interactive docs: http://localhost:8000/docs
   - Alternative docs: http://localhost:8000/redoc

## API Endpoints

### Session Management
- `POST /api/session/init` - Initialize agent session
- `GET /api/session/status` - Get session status
- `POST /api/session/close` - Close session

### Participants
- `POST /api/participants/add` - Add a new participant

### Messages
- `POST /api/messages/send` - Send message from participant and get agent response

## Usage Flow

1. Initialize session
2. Add participants
3. Send messages from participants
4. Receive agent responses

## Development

The API automatically reloads when you save changes (with `--reload` flag).

Check the interactive docs at `/docs` for testing endpoints.
