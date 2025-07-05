from textual_serve.server import Server

server = Server("python3.12 -m nyxbox.main --web", port=80)
server.serve()

