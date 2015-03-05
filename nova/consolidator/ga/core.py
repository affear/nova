import random, operator
from oslo_log import log as logging
from oslo_config import cfg
from oslo_utils import importutils

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

class Gene(object):
    '''
        A gene of our chromosome.
        It is a plain compute node.
        All instances removed.
    '''
    class InstanceWrapper(object):
        def __init__(self, instance):
            '''
                :param:instance: nova.objects.instance.Instance object
            '''
            super(Gene.InstanceWrapper, self).__init__()
            self._instance = instance # hold a hidden reference for copy purpose
            self.id = instance.id
            self.vcpus = instance.vcpus
            self.memory_mb = instance.memory_mb
            self.root_gb = instance.root_gb


    def __init__(self, cn):
        super(Gene, self).__init__()
        self._cn = cn # hold a hidden reference for copy purpose
        self.id = cn.id
        self.vcpus = cn.vcpus
        self.memory_mb = cn.memory_mb
        self.local_gb = cn.local_gb

        running_instances = cn.instances_running
        vcpus_running = reduce(operator.add, [i.flavor.vcpus for i in running_instances], 0)
        ram_running = reduce(operator.add, [i.flavor.memory_mb for i in running_instances], 0)
        disk_running = reduce(operator.add, [i.flavor.root_gb for i in running_instances], 0)

        # getting a clean cn, without running instances.
        # it could be that not all instances are running.
        # in this case we take them as a base and not migrable
        self._base_vcpus_used = cn.vcpus_used - vcpus_running 
        self._base_memory_mb_used = cn.memory_mb_used - ram_running 
        self._base_local_gb_used = cn.local_gb_used - disk_running 

        assert self._base_vcpus_used >= 0
        assert self._base_memory_mb_used >= 0
        assert self._base_local_gb_used >= 0

        # no instances
        self.instances = {}

    def add(self, instance):
        '''
            :param:instance: nova.objects.instance.Instance object
        '''
        iw = self.InstanceWrapper(instance)
        self.instances[iw.id] = iw

        if self.vcpu_r > 1 or self.memory_mb_r > 1 or self.local_gb_r > 1:
            self.remove(iw.id)
            return False

        return True

    def remove(self, instance_id):
        del self.instances[instance_id]

    @property
    def vcpus_used(self):
        return reduce(operator.add, [self.instances[i].vcpus for i in self.instances], self._base_vcpus_used)

    @property
    def memory_mb_used(self):
        return reduce(operator.add, [self.instances[i].memory_mb for i in self.instances], self._base_memory_mb_used)

    @property
    def local_gb_used(self):
        return reduce(operator.add, [self.instances[i].root_gb for i in self.instances], self._base_local_gb_used)

    @property
    def vcpus_free(self):
        return self.vcpus - self.vcpus_used

    @property
    def memory_mb_free(self):
        return self.memory_mb - self.memory_mb_used

    @property
    def local_gb_free(self):
        return self.local_gb - self.local_gb_used


    @property
    def vcpu_r(self):
        return float(self.vcpus_used) / self.vcpus

    @property
    def memory_mb_r(self):
        return float(self.memory_mb_used) / self.memory_mb

    @property
    def local_gb_r(self):
        return float(self.local_gb_used) / self.local_gb


class Chromosome(object):
    '''
        The chromosome is organized as follows:
        - every gene is a compute node
        - the allele is the instances hosted by that cn
    '''
    MUTATION_PROB = CONF.consolidator.prob_mutation

    def __init__(self, genes):
        super(Chromosome, self).__init__()
        self.genes = genes
        self.fitness_function = importutils.import_class(CONF.consolidator.fitness_function)(self)

    @property
    def fitness(self):
        return self.fitness_function.get()

    def _add_instance_to_rnd_gene(self, instance, gene_ids=None):
        if gene_ids is None:
            gene_ids = self.genes.keys()

        gene_ids = list(gene_ids)
        gene_id = random.choice(gene_ids)
        gene = self.genes[gene_id]
        ok = gene.add(instance)
        while not ok:
            gene_ids.remove(gene_id)
            gene_id = random.choice(gene_ids)
            gene = self.genes[gene_id]
            ok = gene.add(instance)

        if not ok:
            raise Exception("Cannot add instance to gene!")

    def mutate(self):
        '''
            Mutation migrates only one instance
        '''
        gene_ids = self.genes.keys()
        gene_ids_cpy = self.genes.keys()

        # choose a suitable gene (instances > 0)
        gene_id = random.choice(gene_ids_cpy)
        instance_ids = self.genes[gene_id].instances
        while len(instance_ids) == 0:
            gene_ids_cpy.remove(gene_id)
            gene_id = random.choice(gene_ids_cpy)
            instance_ids = self.genes[gene_id].instances

        gene_ids.remove(gene_id) # not migrate to same host, please

        gene = self.genes[gene_id]
        instance_id = random.choice(gene.instances.keys())
        instance = gene.instances[instance_id]
        gene.remove(instance_id)
    
        self._add_instance_to_rnd_gene(instance, gene_ids)
        #ok, moved


    def repair(self, all_instances):
        instance_ids = all_instances.keys()
        
        seen = set()
        dups = {g_id: [] for g_id in self.genes}
        for g_id in self.genes:
            gene = self.genes[g_id]
            for i_id in gene.instances:
                if i_id in seen:
                    dups[g_id].append(i_id) # add to duplicates
                else:
                    seen.add(i_id)
                    instance_ids.remove(i_id)

        # remove duplicates:
        for g_id in dups:
            gene = self.genes[g_id]
            for i_id in dups[g_id]:
                gene.remove(i_id)
        
        for i_id in instance_ids:
            # if something is left,
            # this means it is missing.
            # So, add it!
            i = all_instances[i_id]
            self._add_instance_to_rnd_gene(i)
        # ok, repaired

    def copy(self):
        '''
            In-depth copy of chromosome,
            we need it not to mashup things
            when we cross chromosomes
        '''
        genes = {}
        for g_id in self.genes:
            old_gene = self.genes[g_id]
            new_gene = Gene(old_gene._cn)

            for instance_w in old_gene.instances.values():
                ok = new_gene.add(instance_w._instance)
                if not ok:
                    raise Exception('Cannot add instance to chromosome copy!')

            genes[g_id] = new_gene

        return Chromosome(genes)

 
class GA(object):
    LIMIT = CONF.consolidator.epoch_limit
    POP_SIZE = CONF.consolidator.population_size
    CROSSOVER_PROB = CONF.consolidator.prob_crossover
    ELITISM_PERC = CONF.consolidator.elitism_perc
    FITNESS_THRESH = CONF.consolidator.fitness_threshold

    def __init__(self, snapshot):
        super(GA, self).__init__()
        # organizing base data
        self._cns = {}
        cns = snapshot.nodes
        for cn in cns:
            self._cns[cn.id] = cn

        self._all_instances = {}
        instances = snapshot.instances_running
        for i in instances:
            self._all_instances[i.id] = i

        # init population
        self.population = self._get_init_pop()
        self.selection_algorithm_class = importutils.import_class(CONF.consolidator.selection_algorithm)
        self.crossover_function_class = importutils.import_class(CONF.consolidator.crossover_function)
        self.elite_len = int((float(self.ELITISM_PERC) / 100) * self.POP_SIZE)

    def _get_init_pop(self):
        ini_pop = []
        for i in xrange(self.POP_SIZE):
            ini_pop.append(self._rnd_chromo())

        ini_pop.sort(key=lambda ch: ch.fitness)
        return ini_pop

    def _rnd_chromo(self):
        # copy instances
        instance_ids = self._all_instances.keys()
        cn_ids = self._cns.keys()

        instance_used = 0
        total_instances = len(instance_ids)
        genes = {}
        for cn_id in self._cns:
            genes[cn_id] = Gene(self._cns[cn_id])

        while instance_used < total_instances:
            instance_id = random.choice(instance_ids)
            instance = self._all_instances[instance_id]
            cn_id = random.choice(cn_ids)
            gene = genes[cn_id]

            if gene.add(instance):
                instance_ids.remove(instance_id)
                instance_used += 1

        return Chromosome(genes)

    def run(self):
        count = 0
        while count < self.LIMIT and not self._stop():
            if count % 10 == 0:
                LOG.debug('Epoch {}: best individual fitness is {}'.format(
                    count,
                    self.population[0].fitness)
                )
            self.population = self._next()
            self.population.sort(key=lambda ch: ch.fitness)
            count += 1

        LOG.debug('Epoch {}, END: best individual fitness is {}'.format(
            count,
            self.population[0].fitness)
        )
        return self.population[0]

    def _stop(self):
        '''
            Function that checks if we have to stop
            basing on population fitness
        '''
        # ordered population
        return self.population[0].fitness >= self.FITNESS_THRESH

    def _call_with_prob(self, p, method, *args, **kwargs):
        if random.random() > p:
            # do nothing
            return
        return method(*args, **kwargs)
 
    def _next(self):
        next_pop = []
        old_pop = self.population
        # apply elitism
        elite = self._get_elite(old_pop)
        next_pop.extend(elite)

        while len(next_pop) < self.POP_SIZE:
            father = self.selection_algorithm_class(old_pop).get_chromosome()
            mother = self.selection_algorithm_class(old_pop).get_chromosome()

            child = self._evolve(father, mother)
            child.repair(self._all_instances)
            self._call_with_prob(child.MUTATION_PROB, child.mutate)
            next_pop.append(child)

        return next_pop

    def _evolve(self, father, mother):
        father_items = father.genes.items()
        mother_items = mother.genes.items()
        x_function = self.crossover_function_class(father_items, mother_items)
        child_items = self._call_with_prob(self.CROSSOVER_PROB, x_function.cross)
        if not child_items:
            # this means the method wasn't called
            return father

        # create a brand new Chromosome
        return Chromosome(dict(child_items)).copy()

    def _get_elite(self, pop):
        # expect pop is sorted by fitness
        return pop[:self.elite_len]
