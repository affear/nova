import random, operator
from oslo_log import log as logging
from oslo_config import cfg
from oslo_utils import importutils
from nova.consolidator.ga import k

ga_consolidator_opts = [
    cfg.FloatOpt(
        'prob_crossover',
        default=1.0,
        help='The probability to apply crossover'
    ),
    cfg.FloatOpt(
        'prob_mutation',
        default=0.0,
        help='The probability to apply mutation'
    ),
    cfg.StrOpt(
        'selection_algorithm',
        default='nova.consolidator.ga.functions.RouletteSelection',
        help='The selection algorithm used'
    ),
    cfg.StrOpt(
        'crossover_function',
        default='nova.consolidator.ga.functions.SinglePointCrossover',
        help='The crossover function used'
    ),
    cfg.StrOpt(
        'fitness_function',
        default='nova.consolidator.ga.functions.MetricsFitnessFunction',
        help='The fitness function used'
    ),
    cfg.IntOpt(
        'population_size',
        default=500,
        help='The size of population'
    ),
    cfg.IntOpt(
        'epoch_limit',
        default=100,
        help='The maximum number of epochs run in the algorithm'
    ),
    cfg.IntOpt(
        'elitism_perc',
        default=0,
        help='The percentage of the population that will become an elite'
    ),
    cfg.FloatOpt(
        'fitness_threshold',
        default=0.6,
        help='Stop if fitness is higher than threshold'
    ),
]

CONF = cfg.CONF
cons_group = 'consolidator'
CONF.import_group(cons_group, 'nova.consolidator.base')
CONF.register_opts(ga_consolidator_opts, cons_group)

LOG = logging.getLogger(__name__)
 
class GA(object):
    LIMIT = CONF.consolidator.epoch_limit
    POP_SIZE = CONF.consolidator.population_size
    CROSSOVER_PROB = CONF.consolidator.prob_crossover
    MUTATION_PROB = CONF.consolidator.prob_mutation
    ELITISM_PERC = CONF.consolidator.elitism_perc
    FITNESS_THRESH = CONF.consolidator.fitness_threshold

    def __init__(self, snapshot):
        super(GA, self).__init__()

        assert len(snapshot.nodes) > 0, 'Cannot init GA. No nodes given.'
        assert len(snapshot.instances_migrable) > 0, 'Cannot init GA. No migrable instance.'

        ######################
        # organizing base data
        # create hosts tuple
        hosts_dict = {}
        for node in snapshot.nodes:
            locked_instances = node.instances_not_migrable
            base_vcpus = reduce(operator.add, [i.vcpus for i in locked_instances], 0)
            base_ram = reduce(operator.add, [i.memory_mb for i in locked_instances], 0)
            base_disk = reduce(operator.add, [i.root_gb for i in locked_instances], 0)

            vcpus = node.vcpus
            ram = node.memory_mb
            disk = node.local_gb

            hostname = node.host
            base_metrics = (base_vcpus, base_ram, base_disk)
            cap_metrics = (vcpus, ram, disk)

            host_tuple = (base_metrics, cap_metrics)
            hosts_dict[hostname] = host_tuple

        self._base_hosts_dict = hosts_dict

        # create instances dict
        instances_dict = {}
        for instance in snapshot.instances_migrable:
            instance_id = instance.id
            vcpus = instance.vcpus
            ram = instance.memory_mb
            disk = instance.root_gb

            metrics_tuple = (vcpus, ram, disk)
            instances_dict[instance_id] = metrics_tuple

        self._base_instances_dict = instances_dict

        # init functions
        self.selection_algorithm = importutils.import_class(CONF.consolidator.selection_algorithm)()
        self.crossover_function = importutils.import_class(CONF.consolidator.crossover_function)()
        self.fitness_function = importutils.import_class(CONF.consolidator.fitness_function)()
        self.elite_len = int((float(self.ELITISM_PERC) / 100) * self.POP_SIZE)

        # init population
        self.population = self._get_init_pop()

    def run(self):
        '''
            :returns: {hostname: [instance_ids], ...}
        '''
        count = 0
        _log_str = 'Epoch {}: best individual fitness is {}'

        while count < self.LIMIT and not self._stop():
            # log best fitness
            if count % 10 == 0:
                best_fit = self.fitness_function.get(self.population[0])
                LOG.debug(_log_str.format(count, best_fit))

            self.population = self._next()
            self.population.sort(key=lambda ch: self.fitness_function.get(ch))
            count += 1

        best_fit = self.fitness_function.get(self.population[0])
        LOG.debug(' '.join([_log_str, 'END']).format(count, best_fit))

        return {
            hostname: k.get_instance_ids(self.population[0], hostname)
            for hostname in self.population[0]
        }
 
    def _next(self):
        next_pop = []
        old_pop = self.population
        # apply elitism
        elite = self._get_elite(old_pop)
        next_pop.extend(elite)

        while len(next_pop) < self.POP_SIZE:
            father = self.selection_algorithm.get_chromosome(self.population, self.fitness_function)
            mother = self.selection_algorithm.get_chromosome(self.population, self.fitness_function)

            child = self._evolve(father, mother)
            self._repair(child)
            self._call_with_prob(self.MUTATION_PROB, self._mutate, child)
            next_pop.append(child)

        return next_pop

    def _stop(self):
        '''
            Function that checks if we have to stop
            basing on population fitness
        '''
        # ordered population
        return self.fitness_function.get(self.population[0]) >= self.FITNESS_THRESH

    def _call_with_prob(self, p, method, *args, **kwargs):
        if random.random() > p:
            # do nothing
            return
        return method(*args, **kwargs)

    def _get_init_pop(self):
        ini_pop = [self._rnd_chromosome() for i in xrange(self.POP_SIZE)]
        ini_pop.sort(key=lambda ch: self.fitness_function.get(ch))
        return ini_pop

    def _get_suitable_hostnames(self, chromosome, instance_id):
        flavor_tuple = self._base_instances_dict[instance_id]

        vcpus = k.get_vcpus(flavor_tuple)
        ram = k.get_ram(flavor_tuple)
        disk = k.get_disk(flavor_tuple)

        def filtering_function(hostname):
            cap = k.get_cap_from_ch(chromosome, hostname)
            status = k.get_status(chromosome, hostname)

            vcpus_free = k.get_vcpus(cap) - k.get_vcpus(status)
            ram_free = k.get_ram(cap) - k.get_ram(status)
            disk_free = k.get_disk(cap) - k.get_disk(status)

            return vcpus < vcpus_free \
                and ram < ram_free \
                and disk < disk_free

        return filter(filtering_function, chromosome.keys())

    def _get_hostnames_with_instances(self, chromosome):
        def filtering_function(hostname):
            return len(k.get_instance_ids(chromosome, hostname)) > 0

        return filter(filtering_function, chromosome.keys())

    def _copy_chromosome(self, chromosome):
       return { 
            hostname: {
                k.INSTANCE_IDS: list(k.get_instance_ids(chromosome, hostname)),
                k.STATUS: k.get_status(chromosome, hostname),
                k.CAP: k.get_cap_from_ch(chromosome, hostname)
            } for hostname in chromosome}

    def _rnd_chromosome(self):
        # copy base_hosts_dict
        chromosome = {
            hostname: {
                k.INSTANCE_IDS: [],
                k.STATUS: k.get_base(self._base_hosts_dict, hostname),
                k.CAP: k.get_cap(self._base_hosts_dict, hostname)
            } for hostname in self._base_hosts_dict
        }

        for i_id in self._base_instances_dict:
            hostnames = self._get_suitable_hostnames(chromosome, i_id)
            hostname = random.choice(hostnames)
            self._add_instance(chromosome[hostname], i_id)

        return chromosome

    def _add_instance(self, gene, instance_id):
        flavor_tuple = self._base_instances_dict[instance_id]
        status = gene[k.STATUS]
        new_metrics = (
            k.get_vcpus(flavor_tuple) + k.get_vcpus(status),
            k.get_ram(flavor_tuple) + k.get_ram(status),
            k.get_disk(flavor_tuple) + k.get_disk(status)
        )
        gene[k.STATUS] = new_metrics
        gene[k.INSTANCE_IDS].append(instance_id)

    def _remove_instance(self, gene, instance_id):
        flavor_tuple = self._base_instances_dict[instance_id]
        status = gene[k.STATUS]
        new_metrics = (
            k.get_vcpus(status) - k.get_vcpus(flavor_tuple),
            k.get_ram(status) - k.get_ram(flavor_tuple),
            k.get_disk(status) - k.get_disk(flavor_tuple)
        )
        gene[k.STATUS] = new_metrics
        gene[k.INSTANCE_IDS].remove(instance_id)

    def _mutate(self, chromosome):
        # side effect!
        hostnames = self._get_hostnames_with_instances(chromosome)
        hostname = random.choice(hostnames)
        instance_id = random.choice(k.get_instance_ids(chromosome, hostname))

        gene = chromosome[hostname]
        # remove instance from starting host
        self._remove_instance(gene, instance_id)

        # not migrate to same host
        del chromosome[hostname]
        hostnames = self._get_suitable_hostnames(chromosome, instance_id)
        # restore gene
        chromosome[hostname] = gene

        hostname = random.choice(hostnames)
        self._add_instance(chromosome[hostname], instance_id)
        # ok, mutation applied

    def _repair(self, chromosome):
        # side effect!
        # first remove duplicates
        seen = set()
        dups = {hostname: [] for hostname in chromosome}
        for hostname in chromosome:
            for i_id in k.get_instance_ids(chromosome, hostname):
                if i_id in seen:
                    dups[hostname].append(i_id)
                else:
                    seen.add(i_id)

        for hostname in dups:
            for i_id in dups[hostname]:
                self._remove_instance(chromosome[hostname], i_id)

        # then add instances left
        for i_id in self._base_instances_dict:
            if i_id not in seen:
                hostnames = self._get_suitable_hostnames(chromosome, i_id)
                hostname = random.choice(hostnames)
                self._add_instance(chromosome[hostname], i_id)

        # ok, repaired

    def _evolve(self, father, mother):
        child_items = self._call_with_prob(
            self.CROSSOVER_PROB,
            self.crossover_function.cross,
            father.items(), mother.items()
        )
        if not child_items:
            # this means the method wasn't called
            return self._copy_chromosome(father)

        return self._copy_chromosome(dict(child_items))

    def _get_elite(self, pop):
        # expect pop is sorted by fitness
        return pop[:self.elite_len]
