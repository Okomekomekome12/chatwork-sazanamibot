from yt_stream import *
body = "/youtube https://www.youtube.com/watch?v=b2NTglk9tvI"
stream_link = body.split()[1]
print(stream_link)

info = get_stream_links(stream_link)
print(info.url)