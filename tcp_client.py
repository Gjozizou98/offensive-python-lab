import socket 

target_host = "www.google.com"
target_port = 80

# Creation socket object
client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# Client connection
client.connect((target_host, target_port))

# Data send
client.send(b"GET / HTTP/1.1\r\nHost: google.com\r\n\r\n")

# Receive respond
response = client.recv(4096)

print(response.decode())
client.close()