import zmq

context = zmq.Context()
subscriber = context.socket(zmq.SUB)
subscriber.connect("tcp://localhost:5555")  # ZMQ Publisher 주소
subscriber.setsockopt_string(zmq.SUBSCRIBE, "")  # 모든 메시지를 구독

print("Waiting for messages...")
while True:
    message = subscriber.recv_json()
    print(f"Received message: {message}")
