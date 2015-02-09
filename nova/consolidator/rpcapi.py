from oslo_config import cfg
from nova.openstack.common import log as logging
import oslo_messaging as messaging
from nova.objects import base as objects_base
from nova import rpc

rpcapi_opts = [
	cfg.StrOpt(
		'consolidator_topic',
		default='consolidator',
		help='The topic compute nodes listen on'
	),
]

CONF = cfg.CONF
CONF.register_opts(rpcapi_opts)

LOG = logging.getLogger(__name__)

class ConsolidatorAPI(object):

	def __init__(self):
		super(ConsolidatorAPI, self).__init__()
		target = messaging.Target(topic=CONF.consolidator_topic, version='3.0')
		#version_cap = self.VERSION_ALIASES.get(CONF.upgrade_levels.compute, CONF.upgrade_levels.compute)
		serializer = objects_base.NovaObjectSerializer()
		self.client = self.get_client(target, version_cap, serializer)

	def get_client(self, target, version_cap, serializer):
		return rpc.get_client(
			target,
			version_cap=version_cap,
			serializer=serializer
		)

	def log_sth(self, ctxt={}):
		cctxt = self.client.prepare()
		cctxt.cast(ctxt, 'log_sth')