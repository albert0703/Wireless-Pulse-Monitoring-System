import bluetooth

def receive_pulse_data():
    port = 1  # Ensure the same port as the sender
    server_sock = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
    server_sock.bind(("", port))
    server_sock.listen(1)

    print("Waiting for connection...")
    client_sock, address = server_sock.accept()
    print(f"Connection accepted from {address}")

    try:
        while True:
            data = client_sock.recv(1024)  # Buffer size
            if not data:
                break
            print(f"Received data: {data.decode().strip()}")
    except bluetooth.BluetoothError as e:
        print(f"Bluetooth error: {e}")
    except KeyboardInterrupt:
        print("\nKeyboard interrupt detected, exiting...")
    finally:
        client_sock.close()
        server_sock.close()

if __name__ == "__main__":
    receive_pulse_data()
