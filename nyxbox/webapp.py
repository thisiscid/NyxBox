from textual_serve.server import Server

server = Server("python3.12 -m nyxbox.main --web", public_url="https://nyxbox-client.thisisrainy.hackclub.app", port=26345)
server.serve()

