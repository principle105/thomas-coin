from tcoin.tangle.messages import generate_message_lookup

from .discover_peers import DiscoverPeers
from .get_msgs import GetMsgs
from .request import Request

# All the request types
request_types = (DiscoverPeers, GetMsgs)

request_lookup = generate_message_lookup(request_types)
