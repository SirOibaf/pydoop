from abc import ABCMeta, abstractmethod

class ProtocolError(Exception):
    pass

class ProtocolAbort(ProtocolError):
    pass

def toBool(s):
    return s.lower().find('true') > -1

class StreamFilter(object):
    __metaclass__ = ABCMeta
    
    def __init__(self, stream):
        self.stream = stream
    def __iter__(self):
        return self
    def flush(self):
        self.stream.flush()
    def close(self):
        self.stream.close()

class DownStreamFilter(StreamFilter):
    
    CMD_TABLE = {'mapItem'     : ('mapItem', 2, None),
                 'reduceValue' : ('reduceValue', 1, None),
                 'reduceKey'   : ('reduceKey', 1, None),
                 'start'       : ('start', 1, lambda p: [int(p[0]),]),
                 'setJobConf'  : ('setJobConf', None, None),
                 'setInputTypes': ('setInputTypes', 2, None),
                 'runMap' : ('runMap', 3,
                             lambda p: [p[0], int(p[1]), toBool(p[2])]),
                 'runReduce' : ('runReduce', 2,
                                lambda p: [int(p[0]), toBool(p[1])]),
                 'abort' : ('abort', 0, None),
                 'close' : ('close', 0, None),
                 }

    @classmethod
    def convert_message(cls, cmd, args):
        if cmd in cls.CMD_TABLE:
            cmd, nargs, converter = cls.CMD_TABLE[cmd]
            assert nargs is None or len(args) == nargs
            if cmd == 'abort':
                raise ProtocolAbort('received an abort request')
            args = args if converter is None else converter(args)
            return cmd, tuple(args) if args else None
        else:
            raise ProtocolError('Unrecognized command %s' % cmd)

    @abstractmethod
    def next(self):
        pass
        

class UpStreamFilter(StreamFilter):
    CMD_TABLE = {}
    def convert_message(self, cmd, args):
        pass
    @abstractmethod
    def send(self):
        pass
    

class PushBackStream(object):
    def __init__(self, stream):
        self.stream = stream
        self.lifo = []
    def __iter__(self):
        return self
    def next(self):
        if self.lifo:
            return self.lifo.pop()
        return self.stream.next()
    def push_back(self, v):
        self.lifo.append(v)

    
class KeyValuesStream(object):
    def __init__(self, stream):
        self.stream = PushBackStream(stream)
    def __iter__(self):
        return self
    def next(self):
        for cmd, args in self.stream:
            if cmd == 'close':
                raise StopIteration
            elif cmd == 'reduceKey':
                values_stream = self.get_value_stream(self.stream)
                return args[0], values_stream
            elif cmd == 'reduceValue':
                continue
            else:
                raise ProtocolError('out of order command: {}'.format(cmd))     
        raise StopIteration
    @staticmethod
    def get_value_stream(stream):
        for cmd, args in stream:
            if cmd == 'close':
                raise StopIteration
            elif cmd == 'reduceValue':
                yield args[0]
            else:
                stream.push_back((cmd, args))
                raise StopIteration            
        raise StopIteration

def get_key_values_stream(stream):
    return KeyValuesStream(stream)

def get_key_value_stream(stream):
    for cmd, args in stream:
        if cmd == 'close':
            raise StopIteration
        elif cmd == 'mapItem':
            yield args
        else:
            raise ProtocolError('out of order command: {}'.format(cmd))
    raise StopIteration

