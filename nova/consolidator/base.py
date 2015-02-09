class BaseConsolidator(object):

	class Migration(object):
		def __init__(self, instance_id, host_id):
			self.instance_id = instance_id
			self.host_id = host_id

	def consolidate(self):
		# do things
		migs = get_migrations()
		# apply transitive closure to migs
		return migs
		

	def get_migrations(self):
		'''
			Base method to be overridden to obtain consolidation.
			:returns: a list of Migration
		'''
		return []