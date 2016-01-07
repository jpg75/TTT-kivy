'''
Created on 09/mar/2015

@author: Gian Paolo Jesi
'''

import time

class StopWatch:
    def __init__(self, func=time.time):
        self.elapsed = 0.0
        self._func = func
        self._start = None
        self._split = None

    def start(self):
        if self._start is not None:
            raise RuntimeError('Already started')
        self._start = self._func()

    def split(self):
        self._split = self._func() - self._start
        return self._split
        
    def stop(self):
        if self._start is None:
            raise RuntimeError('Not started')
        end = self._func()
        self.elapsed += end - self._start
        self._start = None
    
    def reset(self):
        self.elapsed = 0.0

    def to_string(self, time):
        m, s = divmod(time, 60)
        h, m = divmod(m, 60)
        print time
        print int(s)
        return "%02d:%02d:%02d.%03d" % (h, m, s, int((time - int(s)) * 1000))
        
    @property
    def running(self):
        return self._start is not None

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *args):
        self.stop()
