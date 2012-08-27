import unittest as ut
import os
from abc import ABCMeta, abstractmethod
import volumina._testing
from volumina.pixelpipeline.datasources import ArraySource, RelabelingArraySource
import numpy as np
from volumina.slicingtools import sl, slicing2shape
try:
    import lazyflow
    has_lazyflow = True
except ImportError:
    has_lazyflow = False

if has_lazyflow:
    from lazyflow.graph import Graph
    from volumina.pixelpipeline._testing import OpDataProvider
    from volumina.pixelpipeline.datasources import LazyflowSource, LazyflowSinkSource

class GenericArraySourceTest:
    __metaclass__ = ABCMeta

    @abstractmethod
    def setUp( self ):
        self.source = None

    def testRequestWait( self ):
        slicing = (slice(0,1),slice(10,20), slice(20,25), slice(0,1), slice(0,1))
        requested = self.source.request(slicing).wait()
        self.assertTrue(np.all(requested == self.raw[0:1,10:20,20:25,0:1,0:1]))

    def testRequestNotify( self ):
        slicing = (slice(0,1),slice(10,20), slice(20,25), slice(0,1), slice(0,1))
        request = self.source.request(slicing)
        
        def check(result, codon):
            self.assertTrue(np.all(result == self.raw[0:1,10:20,20:25,0:1,0:1]))
            self.assertEqual(codon, "unique")
        request.notify(check, codon="unique")

    def testSetDirty( self ):
        self.signal_emitted = False
        self.slicing = (slice(0,1),slice(10,20), slice(20,25), slice(0,1), slice(0,1))

        def slot( sl ):
            self.signal_emitted = True
            self.assertTrue( sl == self.slicing )

        self.source.isDirty.connect(slot)
        self.source.setDirty( self.slicing )
        self.source.isDirty.disconnect(slot)

        self.assertTrue( self.signal_emitted )

        del self.signal_emitted
        del self.slicing
    
    def testComparison(self):
        assert self.samesource == self.source
        assert self.othersource != self.source

class ArraySourceTest( ut.TestCase, GenericArraySourceTest ):
    def setUp( self ):
        self.lena = np.load(os.path.join(volumina._testing.__path__[0], 'lena.npy'))
        self.raw = np.zeros((1,512,512,1,1))
        self.raw[0,:,:,0,0] = self.lena
        self.source = ArraySource( self.raw )
        
        self.samesource = ArraySource( self.raw )
        self.othersource = ArraySource( np.array(self.raw) )

class RelabelingArraySourceTest( ut.TestCase, GenericArraySourceTest ):
    def setUp( self ):
        a = np.zeros((5,1,1,1,1), dtype=np.uint32)
        #the data contained in a ranges from [1,5]
        a[:,0,0,0,0] = np.arange(0,5)
        self.source = RelabelingArraySource(a)

        #we apply the relabeling i -> i+1
        relabeling = np.arange(1,a.max()+2, dtype=np.uint32)
        self.source.setRelabeling(relabeling)

        self.samesource = RelabelingArraySource(a)
        self.othersource = RelabelingArraySource( np.array(a) )

    def testRequestWait( self ):
        slicing = (slice(0,5),slice(None), slice(None), slice(None), slice(None))
        requested = self.source.request(slicing).wait()
        assert requested.ndim == 5
        self.assertTrue(np.all(requested.flatten() == np.arange(1,6, dtype=np.uint32)))

    def testRequestNotify( self ):
        slicing = (slice(0,5),slice(None), slice(None), slice(None), slice(None))
        request = self.source.request(slicing)
        
        def check(result, codon):
            self.assertTrue(np.all(result.flatten() == np.arange(1,6, dtype=np.uint32)))
            self.assertEqual(codon, "unique")
        request.notify(check, codon="unique")

    def testSetDirty( self ):
        self.signal_emitted = False
        self.slicing = (slice(0,5),slice(None), slice(None), slice(None), slice(None))

        def slot( sl ):
            self.signal_emitted = True
            self.assertTrue( sl == self.slicing )

        self.source.isDirty.connect(slot)
        self.source.setDirty( self.slicing )
        self.source.isDirty.disconnect(slot)

        self.assertTrue( self.signal_emitted )

        del self.signal_emitted
        del self.slicing


if has_lazyflow:
    class LazyflowSourceTest( ut.TestCase, GenericArraySourceTest ):
        def setUp( self ):
            self.lena = np.load(os.path.join(volumina._testing.__path__[0], 'lena.npy'))
            self.raw = np.zeros((1,512,512,1,1), dtype=np.uint8)
            self.raw[0,:,:,0,0] = self.lena

            g = Graph()
            op = OpDataProvider(g, self.raw)
            self.source = LazyflowSource( op.Data )

            self.samesource = LazyflowSource( op.Data )
            opOtherData = OpDataProvider(g, self.raw)
            self.othersource = LazyflowSource( opOtherData.Data )
        
    class LazyflowSinkSourceTest( ut.TestCase, GenericArraySourceTest ):
        def setUp( self ):
            self.lena = np.load(os.path.join(volumina._testing.__path__[0], 'lena.npy'))
            self.raw = np.zeros((1,512,512,1,1), dtype=np.uint8)
            self.raw[0,:,:,0,0] = self.lena

            g = Graph()
            self.op = OpDataProvider(g, self.raw)
            self.source = LazyflowSinkSource(self.op.Data, self.op.Changedata)

            self.samesource = LazyflowSinkSource(self.op.Data, self.op.Changedata)
            opOtherData = OpDataProvider(g, self.raw)
            self.othersource = LazyflowSinkSource(opOtherData.Data, self.op.Changedata)
        
        def testPut(self):
            slicing = sl[0:1, 0:100, 0:100, 0:1, 0:1]
            inData = (255*np.random.random( slicing2shape(slicing) )).astype(np.uint8)

            # Put some data into the source and get it back out again
            self.source.put(slicing, inData)
            req = self.source.request(slicing)
            assert (req.wait() == inData).all()
            

if __name__ == '__main__':
    ut.main()











