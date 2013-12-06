import cyclone.escape
import cyclone.web
import cyclone.redis
import cyclone.websocket
import os.path
import sys
from twisted.python import log
from twisted.internet import reactor
from twisted.application import internet
from twisted.application import service

REDIS ={
    'server': '127.0.0.1',
    'port': 6379,
    'sub_channel': 'REBUILD',
}

class Application(cyclone.web.Application):
    def __init__(self):
        handlers = [
            (r"/", MainHandler),
        ]
        cyclone.web.Application.__init__(self, handlers)


class MainHandler(cyclone.websocket.WebSocketHandler):
    clients = []

    def connectionMade(self):
        log.msg("ws: someone connected")
        self.clients.append(self)

    def connectionLost(self, *args, **kwargs):
        log.msg('ws: someone disconnected')
        self.clients.remove(self)


class RedisProtocol(cyclone.redis.SubscriberProtocol):
    def connectionMade(self):
        print "redis: waiting for messages..."
        self.subscribe(REDIS['sub_channel'])

    def messageReceived(self, pattern, channel, message):
        print "redis: got message {} in channel {}".format(message, channel)
        for client in MainHandler.clients:
            client.sendMessage(message)

    def connectionLost(self, reason):
        print "redis: lost connection:", reason


class RedisFactory(cyclone.redis.SubscriberFactory):
    # SubscriberFactory is a wapper for the ReconnectingClientFactory
    maxDelay = 120
    continueTrying = True
    protocol = RedisProtocol


def main():
    reactor.listenTCP(9001, Application())
    reactor.connectTCP(REDIS['server'], REDIS['port'], RedisFactory())
    reactor.run()


if __name__ == "__main__":
    log.startLogging(sys.stdout)
    main()