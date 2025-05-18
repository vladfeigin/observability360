# board_orchestrator_sse.py
"""
SSE-based orchestrator for a two-engine chess game:

  • Connects to white_agent_sse.py and black_agent_sse.py via HTTP/SSE
  • Calls their `move` tool alternately, validates the moves,
    maintains a python-chess board, renders a tiny GUI,
    and logs all events.

Requires:
 uv add autogen-agentchat autogen-ext[openai,mcp] python-chess chess-board rich
Run from the root of the repository: python -m mcp_sse.board
"""
import asyncio
import json
import os
import logging
import chess
import chess.pgn
from chessboard import display
from autogen_ext.tools.mcp import McpWorkbench, SseServerParams
from otel.otel import configure_telemetry, trace_span

"""
# configure logging
logging.basicConfig(
    level=logging.INFO,
    format="[Board] %(asctime)s %(levelname)s: %(message)s",
    datefmt="%H:%M:%S"
)
log = logging.getLogger("board")
"""

SERVICE_VERSION = "1.0.1"

instruments = configure_telemetry("Board Service", SERVICE_VERSION)
meter = instruments["meter"]
tracer = instruments["tracer"]
log = instruments["logger"]

# endpoints for SSE agents
WHITE_URL = os.getenv("WHITE_URL", "http://localhost:8001")
BLACK_URL = os.getenv("BLACK_URL", "http://localhost:8002")

@trace_span("Start the game...", tracer)
async def run() -> None:
    
    board = chess.Board()
    
    # initialize UI with the starting FEN
    game_board = display.start(board.fen())

    # configure SSE workbenches
    wb_white = McpWorkbench(
        SseServerParams(url=f"{WHITE_URL}/sse", timeout=90)
    )
    wb_black = McpWorkbench(
        SseServerParams(url=f"{BLACK_URL}/sse", timeout=90)
    )

    async with wb_white, wb_black:
        current_wb, current_name = wb_white, "white"
        other_wb, other_name     = wb_black, "black"
        max_invalid = 50
        invalid_count = 0

        while not board.is_game_over():
            fen = board.fen()
            log.info(f"Requesting {current_name} move. FEN={fen}")

            with tracer.start_as_current_span("move_span") as span:
                span.set_attribute("fen", fen)
                span.set_attribute("current_player", current_name)
                # call the remote move tool
                result = await current_wb.call_tool("move", {"fen": fen})
                # parse SSE chunked response
                content = result.result[0].content
                log.info("Current move is :", content)
                if not content or 'uci' not in content:
                    invalid_count += 1
                    log.warning(f"{current_name} agent error ({invalid_count}/{max_invalid}): {content}")
                    if invalid_count <= max_invalid:
                        await asyncio.sleep(1)
                        continue
                    else:
                        log.error("1.Too many invalid moves; aborting game.")
                        break
                invalid_count = 0
                
                try:
                    payload = json.loads(content)
                except json.JSONDecodeError:
                    log.error(f"Fatal Error: Invalid JSON from {current_name}: {content}")
                    break

                if not payload or 'uci' not in payload:
                    invalid_count += 1
                    log.warning(f"{current_name} agent error ({invalid_count}/{max_invalid}): {payload}")
                    if invalid_count >= max_invalid:
                        log.error("2.Too many invalid moves; aborting game.")
                        break
                    continue
            
                invalid_count = 0
                uci = payload['uci']
                log.info(f"Received UCI from {current_name}: {uci}")
                span.set_attribute("uci", uci)

            # validate move
            try:
                mv = chess.Move.from_uci(uci)
                if mv not in board.legal_moves:
                    raise ValueError("illegal move")
            except Exception as e:
                log.error(f"Illegal move from {current_name}: {uci} ({e})")
                break

            # apply and render
            board.push(mv)
            display.update(board.fen(), game_board)
            log.info(f"Applied move {uci}")
           
            # swap turns
            current_wb, other_wb       = other_wb, current_wb
            current_name, other_name   = other_name, current_name
            await asyncio.sleep(2)

    # game over summary
    result = board.result()
    reason = ("Checkmate" if board.is_checkmate() else
              "Stalemate" if board.is_stalemate() else
              "Insufficient material" if board.is_insufficient_material() else
              "Fifty-move rule" if board.can_claim_fifty_moves() else
              "Threefold repetition" if board.can_claim_threefold_repetition() else
              "Unknown")
    log.info(f"Game over: {result} - {reason}")

    # export PGN
    game = chess.pgn.Game.from_board(board)
    with open("game_record.pgn", "w") as f:
        f.write(str(game))
    log.info("Game saved to game_record.pgn")

    display.terminate()
    await asyncio.sleep(2)

if __name__ == "__main__":
    # URLs may include /sse or root depending on agent setup
    log.info("Starting Board Orchestrator (SSE)!")
    asyncio.run(run())
