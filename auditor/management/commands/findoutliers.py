from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.core.mail import send_mail
from django.db.models import Count

import numpy as np
import pandas as pd
import math
import statsmodels.formula.api as smf
import re

from auditor.models import HITType, HIT, Worker, Assignment, AssignmentDuration, AssignmentAudit, Requester

"""
Uses singular value decomposition to create a vector factorization of the task-worker matrix.
This can be tested to identify if a worker is way out of the normal self-report bounds,
as when their item in the worker vector is very unusually scaled.
"""

class Command(BaseCommand):
    help = 'Calculate SVD vector factorization of the task-worker matrix'

    def handle(self, *args, **options):
        self.__create_sparse_matrix()

    def __create_sparse_matrix(self):

        self.stdout.write("Creating work matrix...")
        if settings.DEBUG:
            try:
                df = pd.read_pickle('workmatrixOLS.pickle')
            except IOError:
                df = self.read_data()
                df.to_pickle('workmatrixOLS.pickle')
        else:
            df = self.read_data()

        weights = self.model_weights(df)
        self.identify_outliers(weights)

    def read_data(self):
        # only consider workers who had at least two reports
        workers = Worker.objects.annotate(num_durations=Count('assignment__assignmentduration')).filter(num_durations__gte = 2)
        m = len(workers)
        self.stdout.write("%d workers have enough data" % m)

        # only look at HITTypes that had reports from at least two distinct workers
        hittypes = HITType.objects.annotate(num_distinct_workers=Count('hit__assignment__assignmentduration__assignment__worker', distinct=True)).filter(num_distinct_workers__gte = 2)
        n = len(hittypes)
        self.stdout.write("%d HIT Types have enough data" % n)

        dfpy = []
        for widx, worker in enumerate(workers):
            self.stdout.write("Worker %d of %d" % (widx+1, m))
            for hidx, hittype in enumerate(hittypes):
                durations = AssignmentDuration.objects.filter(assignment__worker = worker).filter(assignment__hit__hit_type = hittype)
                for duration in durations:
                    #median_report = np.median([d.duration.total_seconds() for d in durations])
                    dfpy.append({ 'worker': worker.id, 'hit_type': hittype.id, 'log_report': math.log(duration.duration.total_seconds())})
        df = pd.DataFrame(dfpy)
        return df

    def model_weights(self, df):
        mod = smf.ols(formula='log_report ~ worker + hit_type', data=df)
        result = mod.fit()
        print(result.summary())
        print("TODO: find a reasonable baseline worker to set as intercept")
        worker_weights = result.params.filter(regex='worker')#.sort_values(by=[''])
        worker_weights = worker_weights.sort_values()
        print(worker_weights)
        return worker_weights

    def identify_outliers(self, worker_weights):
        # print out info for the interesting workers
        self.stderr.write(self.style.ERROR('Outliers\n-----------'))
        for i in range(-5, 0):
            workerindex = worker_weights.index[i]
            workerid = re.search('worker\[T\.(.*)\]', workerindex).group(1)
            worker = Worker.objects.get(id = workerid)
            self.__report_worker(worker)

    def __report_worker(self, worker):
        self.stdout.write(self.style.ERROR("Worker: %s" % worker.id))
        worker_hittypes = HITType.objects.filter(hit__assignment__worker=worker).distinct()
        for worker_hittype in worker_hittypes:
            worker_median_durations = list()
            worker_hittype_allworkers = Worker.objects.filter(assignment__hit__hit_type = worker_hittype).distinct()
            if len(worker_hittype_allworkers) > 1:
                for worker_hittype_worker in worker_hittype_allworkers:
                    worker_hittype_worker_durations = AssignmentDuration.objects.filter(assignment__hit__hit_type = worker_hittype).filter(assignment__worker = worker_hittype_worker)
                    if len(worker_hittype_worker_durations) > 0:
                        median_report = np.median([d.duration.total_seconds() for d in worker_hittype_worker_durations])
                        worker_median_durations.append( { 'worker': worker_hittype_worker, 'median': median_report})

            if len(worker_median_durations) > 1 and worker in [d['worker'] for d in worker_median_durations]:
                self.stdout.write("HIT Type: %s" % (worker_hittype.id))
                worker_median_durations.sort(key=lambda x: x['median'])
                for worker_median_duration in worker_median_durations:
                    s = "\tWorker %s: median %f" % (worker_median_duration['worker'].id, worker_median_duration['median'])
                    if worker_median_duration['worker'] == worker:
                        self.stderr.write(self.style.WARNING(s))
                    else:
                        self.stdout.write(s)
