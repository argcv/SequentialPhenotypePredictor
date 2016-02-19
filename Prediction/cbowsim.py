import argparse
import math
from binarypredictor import BinaryPredictor


class CbowSim(BinaryPredictor):

    def __init__(self, filename, window=10, size=600, decay=5, stopwords=0, threshold=0.5,
                 balanced=False):
        self._window = window
        self._size = size
        self._decay = decay
        self._stopwords = stopwords
        self._stopwordslist = []
        self._props = {"window": window, "size": size, "decay": decay, "stopwords": stopwords,
                       "balanced": balanced}
        super(CbowSim, self).__init__(filename)

    def train(self, filename):
        self.base_train(filename)

        self._sim_mat = {}
        for diag in self._diags:
            words = self._model.most_similar(diag, topn=len(self._uniq_events))
            sim_array = [0] * len(self._uniq_events)
            sim_array[self._events_index.index(diag)] = 1
            for event, distance in words:
                sim_array[self._events_index.index(event)] = distance
            self._sim_mat[diag] = sim_array

    def predict(self, feed_events):
        predictions = {}
        te = len(feed_events)
        test_array = [0] * len(self._uniq_events)
        for i, e in enumerate(feed_events):
            test_array[self._events_index.index(e)] += math.exp(self._decay*(i-te+1)/te)

        for diag in self._diags:
            sim_array = self._sim_mat[diag]
            dot_product = sum([(x*y) for x, y in zip(test_array, sim_array)])
            prediction = dot_product / len(feed_events)
            if prediction > 1:
                prediction = 1
            elif prediction < 0:
                prediction = 0
            predictions[diag] = prediction

        return predictions

    def test(self, filename):
        with open(filename) as f:
            for line in f:
                feed_events = line.split("|")[2].split(" ")
                feed_events = [w for w in feed_events if w not in self._stopwordslist]
                actual = line.split("|")[0].split(",")
                predictions = self.predict(feed_events)
                for diag in self._diags:
                    self.stat_prediction(predictions[diag], (diag in actual), diag,
                                         (diag in feed_events))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='CBOW Similarity')
    parser.add_argument('-w', '--window', action="store", default=10, type=int,
                        help='Set max skip length between words (default: 10)')
    parser.add_argument('-s', '--size', action="store", default=600, type=int,
                        help='Set size of word vectors (default: 600)')
    parser.add_argument('-d', '--decay', action="store", default=5, type=float,
                        help='Set exponential decay through time (default: 5)')
    parser.add_argument('-sw', '--stopwords', action="store", default=0, type=int,
                        help='Set number of stop words (default: 0)')
    parser.add_argument('-b', '--balanced', action="store", default=False, type=bool,
                        help='Whether to use balanced or not blanaced datasets')
    args = parser.parse_args()

    train_files = []
    test_files = []
    data_path = "../Data/seq_combined/"
    if args.balanced:
        data_path = "../Data/seq_combined_balanced/"

    model = CbowSim(data_path + 'mimic_train_0', args.window, args.size, args.decay,
                    args.stopwords, args.balanced)

    for i in range(10):
        train_files.append(data_path + 'mimic_train_'+str(i))
        test_files.append(data_path + 'mimic_test_'+str(i))

    model.cross_validate(train_files, test_files)
    model.write_stats()
    print(model.accuracy)
