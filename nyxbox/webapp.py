from textual_serve.server import Server

server = Server("python -m nyxbox.main --web")
server.serve()