# One of the two only good functions from PHP. The
# other one is get_file_contents()
def put_file_contents(filename, data):
    with open(filename, 'wb') as f:
        f.write(data.encode())
