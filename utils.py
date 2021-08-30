# One of the two only good functions from PHP. The other one is get_file_contents()
def put_file_contents(filename, data):
    with open(filename, 'wb') as f:
        f.write(data.encode())

# Hey, here's the second one
def get_file_contents(filename):
    with open(filename, 'r', encoding='utf-8') as f:
        return f.read()

def chop(s, sep=None):
    chunks = s.split(sep=sep, maxsplit=1)
    if len(chunks) == 0:
        return '', ''
    elif len(chunks) == 1:
        return chunks[0], ''
    else:
        return chunks[0], chunks[1]

def delete_file(filename):
    import os

    try:
        os.remove(filename)
    except FileNotFoundError:
        pass