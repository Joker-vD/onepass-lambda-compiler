# One of the two only good functions from PHP. The other one is get_file_contents()
def put_file_contents(filename, data):
    with open(filename, 'wb') as f:
        f.write(data.encode())

def chop(s):
    chunks = s.split(maxsplit=1)
    if len(chunks) == 0:
        return '', ''
    elif len(chunks) == 1:
        return chunks[0], ''
    else:
        return chunks[0], chunks[1]
