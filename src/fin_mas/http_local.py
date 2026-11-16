"""Servidor HTTP de loopback sem a consulta de nome do `http.server`.

`HTTPServer.server_bind` chama `socket.getfqdn(host)`, uma consulta DNS reversa, só para preencher
`server_name` (usado por CGI, que o projeto não usa). Em alguns macOS, como o runner da CI, essa
consulta leva dezenas de segundos e o servidor demora a escutar: o ERP de demonstração não respondia
ao roteiro Playwright das fontes em 20 s. O nome aqui é o próprio endereço de loopback.
"""
import socketserver
from http.server import ThreadingHTTPServer


class ServidorLocal(ThreadingHTTPServer):
    def server_bind(self) -> None:
        socketserver.TCPServer.server_bind(self)
        host, porta = self.server_address[:2]
        self.server_name, self.server_port = str(host), porta
