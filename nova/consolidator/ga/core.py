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

# >>> import timeit
# >>> timeit.timeit('tuple(i for i in xrange(1000))')
# 52.415825843811035
# >>> timeit.timeit('[i for i in xrange(1000)]')
# 31.806253910064697
# >>> timeit.timeit('{i: i for i in xrange(1000)}')
# 53.94730615615845
#
# - we use LISTS
# - the cromosome is a LIST containing hostnames
# - each element is in the same position as in snapshot.instances_migrable
# - we don't repair. If crossover goes bad, father will be returned

def _call_with_prob(p, method, *args, **kwargs):
    if random.random() > p:
        # do nothing
        return None
    return method(*args, **kwargs)

class GA(object):
    LIMIT = CONF.consolidator.epoch_limit
    POP_SIZE = CONF.consolidator.population_size
    CROSSOVER_PROB = CONF.consolidator.prob_crossover
    MUTATION_PROB = CONF.consolidator.prob_mutation
    ELITISM_PERC = CONF.consolidator.elitism_perc
    FITNESS_THRESH = CONF.consolidator.fitness_threshold

    def __init__(self, snapshot):
        super(GA, self).__init__()
        self._instances = snapshot.instances_migrable
        self._no_instances = len(self._instances)

        assert len(snapshot.nodes) > 0, 'Cannot init GA. No nodes given.'
        assert  self._no_instances > 0, 'Cannot init GA. No migrable instance.'

        # create hosts dict.
        # we create it only the first time at init.
        # nodes should be a few compared to instances
        def get_base_cap_tuple(node):
            locked_instances = node.instances_not_migrable

            if len(locked_instances) == 0:
                base_tuple = (0, 0, 0)
            else:
                base_list = [(i.vcpus, i.memory_mb, i.root_gb) for i in locked_instances]
                base_tuple = tuple(sum(m) for m in zip(*base_list))

            cap_metrics = (node.vcpus, node.memory_mb, node.local_gb)

            return (base_tuple, cap_metrics)

        self._hosts = {node.host: get_base_cap_tuple(node) for node in snapshot.nodes}
        self._flavors = [(i.vcpus, i.memory_mb, i.root_gb) for i in self._instances]
        self._indexes = list(range(self._no_instances))

        # init functions
        self.selection_algorithm = importutils.import_class(CONF.consolidator.selection_algorithm)()
        self.crossover_function = importutils.import_class(CONF.consolidator.crossover_function)()
        self.fitness_function = importutils.import_class(CONF.consolidator.fitness_function)()
        self.elite_len = int((float(self.ELITISM_PERC) / 100) * self.POP_SIZE)

        # init population
        self.population = self._get_init_pop()

    def run(self):
        '''
            :returns: hostname list indexed as snapshot.instances_migrable
        '''
        count = 0
        _log_str = 'Epoch {}: best individual fitness is {}'

        while count < self.LIMIT and not self._stop():
            # log best fitness
            if count % 10 == 0:
                best_fit = self._get_fitness(self.population[0])
                LOG.debug(_log_str.format(count, best_fit))

            self.population = self._next()
            self.population.sort(key=lambda ch: self._get_fitness(ch))
            count += 1

        best_fit = self._get_fitness(self.population[0])
        LOG.debug(' '.join([_log_str, 'END']).format(count, best_fit))

        return {inst.id: self.population[0][i] for i, inst in enumerate(self._instances)}
 
    def _next(self):
        chromosomes_left = self.POP_SIZE - self.elite_len

        def new_chromosome():
            father = self.selection_algorithm.get_chromosome(self.population, self._get_fitness)
            mother = self.selection_algorithm.get_chromosome(self.population, self._get_fitness)

            child = self._evolve(father, mother)
            _call_with_prob(self.MUTATION_PROB, self._mutate, child)
            return child

        new_pop = self._get_elite(self.population)
        new_pop.extend([new_chromosome() for i in xrange(chromosomes_left)])
        return new_pop

    def _stop(self):
        # ordered population
        return self._get_fitness(self.population[0]) >= self.FITNESS_THRESH

    def _get_init_pop(self):
        ini_pop = [self._rnd_chromosome() for i in xrange(self.POP_SIZE)]
        ini_pop.sort(key=lambda ch: self._get_fitness(ch))
        return ini_pop

    def _get_status(self, chromosome, hostname):
        indexes = filter(lambda i: chromosome[i] == hostname, self._indexes)
        metrics = [self._flavors[i] for i in indexes]
        # add the base to future sum
        metrics.append(k.get_base(self._hosts, hostname))
        return tuple(sum(m) for m in zip(*metrics))

    def _get_ratios(self, chromosome):
        def extract_ratio(hostname):
            status_tuple = self._get_status(chromosome, hostname)

            status_vcpus = k.get_vcpus(status_tuple) 
            status_ram = k.get_ram(status_tuple) 
            status_disk = k.get_disk(status_tuple) 

            cap_vcpus = k.get_vcpus(k.get_cap(self._hosts, hostname))
            cap_ram = k.get_ram(k.get_cap(self._hosts, hostname))
            cap_disk = k.get_disk(k.get_cap(self._hosts, hostname))

            return (
                float(status_vcpus) / cap_vcpus,
                float(status_ram) / cap_ram,
                float(status_disk) / cap_disk
            )

        return [extract_ratio(hostname) for hostname in self._hosts.keys()]

    def _validate_chromosome(self, chromosome):
        return not any(r > 1 for r in self._get_ratios(chromosome))

    def _get_suitable_hostnames(self, instance_index, status):
        def host_ok(hostname):
            cap = k.get_cap(self._hosts, hostname)
            residuals = (
                k.get_vcpus(cap) - k.get_vcpus(status[hostname]) - k.get_vcpus(self._flavors[instance_index]),
                k.get_ram(cap) - k.get_ram(status[hostname]) - k.get_ram(self._flavors[instance_index]),
                k.get_disk(cap) - k.get_disk(status[hostname]) - k.get_disk(self._flavors[instance_index])
            )
            return all(residual >= 0 for residual in residuals)

        return filter(host_ok, self._hosts.keys())

    def _rnd_chromosome(self):
        status = {h: k.get_base(self._hosts, h) for h in self._hosts.keys()}

        def add_to_host(index):
            hostnames = self._get_suitable_hostnames(index, status)
            hostname = random.choice(hostnames)
            status[hostname] = (
                k.get_vcpus(status[hostname]) + k.get_vcpus(self._flavors[index]),
                k.get_ram(status[hostname]) + k.get_ram(self._flavors[index]),
                k.get_disk(status[hostname]) + k.get_disk(self._flavors[index])
            )
            return hostname

        return [add_to_host(i) for i in xrange(self._no_instances)]

    def _mutate(self, chromosome):
        # ! side effect
        i = random.randint(0, self._no_instances - 1)
        status = {h: self._get_status(chromosome, h) for h in self._hosts.keys()}
        hostname = chromosome[i]
        status[hostname] = k.get_cap(self._hosts, hostname) # will never be suitable
        hostnames = self._get_suitable_hostnames(i, status)
        chromosome[i] = random.choice(hostnames)

    def _evolve(self, father, mother):
        child = _call_with_prob(
            self.CROSSOVER_PROB,
            self.crossover_function.cross,
            father, mother
        )
        if child is None or not self._validate_chromosome(child):
            return list(father)
        return child

    def _get_fitness(self, chromosome):
        return self.fitness_function.get(self._get_ratios(chromosome))

    def _get_elite(self, pop):
        # expect pop is sorted by fitness
        return pop[:self.elite_len]
