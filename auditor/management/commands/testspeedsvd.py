from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.core.mail import send_mail
from django.db.models import Count

import numpy as np
from scipy.sparse import csr_matrix, lil_matrix, save_npz, load_npz
from scipy.sparse.linalg import svds
from sklearn.preprocessing import LabelEncoder, OneHotEncoder

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
        workers = Worker.objects.annotate(num_durations=Count('assignment__assignmentduration')).filter(num_durations__gte = 3).order_by('id')
        m = len(workers)
        self.stdout.write("%d" % m)

        hittypes = HITType.objects.annotate(num_durations=Count('hit__assignment__assignmentduration')).filter(num_durations__gte = 3).order_by('id')
        n = len(hittypes)
        self.stdout.write("%d" % n)

        self.stdout.write("Creating sparse work matrix...")
        try:
            A = load_npz('/Users/msb/Documents/fairwork-server/fairwork-server/workmatrix.npz')
        except IOError:
            A_lil = lil_matrix((m, n), dtype=np.float64)
            for widx, worker in enumerate(workers):
                self.stdout.write("Worker %d of %d" % (widx+1, m))
                for hidx, hittype in enumerate(hittypes):
                    durations = AssignmentDuration.objects.filter(assignment__worker = worker).filter(assignment__hit__hit_type = hittype)
                    if len(durations) > 0:
                        median_report = np.median([d.duration.total_seconds() for d in durations])
                        A_lil[widx, hidx] = math.log(median_report)
            A = A_lil.tocsr()
            save_npz('/Users/msb/Documents/fairwork-server/fairwork-server/workmatrix.npz', A)
        print(A)


        u, s, vt = svds(A, k=1)
        print(u)
        #self.stdout.write(vt)
        print(s)

        sorted_workers = list()
        for widx, worker in enumerate(workers):
            sorted_workers.append({ 'worker': worker, 'value': s * u[widx]})
        sorted_workers.sort(key= lambda x: x['value'])
        print(sorted_workers)

        # print out info for the interesting workers
        self.stderr.write(self.style.ERROR('FIRST'))
        for i in range(0, 4):
            worker = sorted_workers[i]['worker']
            self.__report_worker(worker)
        self.stderr.write(self.style.ERROR('LAST'))
        for i in range(-4, 0):
            worker = sorted_workers[i]['worker']
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
