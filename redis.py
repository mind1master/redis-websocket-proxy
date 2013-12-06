import collections
import cyclone.redis

class QueueProtocol(cyclone.redis.SubscriberProtocol, RedisMixin):
    def messageReceived(self, pattern, channel, message):
        # When new messages are published to Redis channels or patterns,
        # they are broadcasted to all HTTP clients subscribed to those
        # channels.
        RedisMixin.broadcast(self, pattern, channel, message)

    def connectionMade(self):
        RedisMixin.psconn = self

        # If we lost connection with Redis during operation, we
        # re-subscribe to all channels once the connection is re-established.
        for channel in self.channels:
            if "*" in channel:
                self.psubscribe(channel)
            else:
                self.subscribe(channel)

    def connectionLost(self, why):
        RedisMixin.psconn = None


class RedisMixin(object):
    dbconn = None
    psconn = None
    channels = collections.defaultdict(lambda: [])

    @classmethod
    def setup(self, host, port, dbid, poolsize):
        # PubSub client connection
        qf = cyclone.redis.SubscriberFactory()
        qf.maxDelay = 20
        qf.protocol = QueueProtocol
        reactor.connectTCP(host, port, qf)

        # Normal client connection
        RedisMixin.dbconn = cyclone.redis.lazyConnectionPool(host, port,
                                                             dbid, poolsize)

    def subscribe(self, channel):
        if RedisMixin.psconn is None:
            raise cyclone.web.HTTPError(503)  # Service Unavailable

        if channel not in RedisMixin.channels:
            log.msg("Subscribing entire server to %s" % channel)
            if "*" in channel:
                RedisMixin.psconn.psubscribe(channel)
            else:
                RedisMixin.psconn.subscribe(channel)

        RedisMixin.channels[channel].append(self)
        log.msg("Client %s subscribed to %s" %
                (self.request.remote_ip, channel))

    def unsubscribe_all(self, ign):
        # Unsubscribe peer from all channels
        for channel, peers in RedisMixin.channels.iteritems():
            try:
                peers.pop(peers.index(self))
            except:
                continue

            log.msg("Client %s unsubscribed from %s" %
                    (self.request.remote_ip, channel))

            # Unsubscribe from channel if no peers are listening
            if not len(peers) and RedisMixin.psconn is not None:
                log.msg("Unsubscribing entire server from %s" % channel)
                if "*" in channel:
                    RedisMixin.psconn.punsubscribe(channel)
                else:
                    RedisMixin.psconn.unsubscribe(channel)

    def broadcast(self, pattern, channel, message):
        peers = self.channels.get(pattern or channel)
        if not peers:
            return

        # Broadcast the message to all peers in channel
        for peer in peers:
            # peer is an HTTP client, RequestHandler
            peer.write("%s: %s\r\n" % (channel, message))
            peer.flush()