import docker

client = docker.from_env()


container = client.containers.run(
    "ubuntu:latest",
    detach=True,
    command="/bin/bash",
    tty=True,
    stdin_open=True,
)

command = input("Enter command to run in container, type exit to end: ")

while True:
    if command == "exit":
        break
    else:
        exec_log = container.exec_run(command)
        print(exec_log.output.decode())
        command = input("Enter command to run in container, type exit to end: ")

container.stop()
container.remove()