import fastBPE
from ozone.puzzle import one_hot, PuzzleGenerator
from ozone.cuda import FloatTensor, cudaify

class BpePuzzleGenerator(PuzzleGenerator):
    """
    Generate the tokenized puzzle
    
    """
    def __init__(self, base_puzzle_gen, vocab, bpe):
        super(BpePuzzleGenerator, self).__init__()
        self.vocab = vocab
        self.bpe = bpe
        self.base_puzzle_gen = base_puzzle_gen
        
    @staticmethod
    def _read_vocab(vocab_file_path):
        with open(vocab_file_path) as reader:
            vocab = [(line.split()[0], i) for (i, line) in enumerate(reader)]
            tok_to_ix = dict(vocab)
        return tok_to_ix

    def max_tokens_per_choice(self):
        return 5
     
    def get_vocab(self):
        return self.vocab

    def generate(self):
        '''
        e.g
        result = [([['app', 'le'], ['pea', 'r']] , 0), 
                  ([['do', 'g'], ['ca', 't']], 1), 
                  ([['low', 'er'], ['high', 'er']] 0)]
        '''
        puzzle = self.base_puzzle_gen.generate()
        tok_puzzle = self.bpe.apply(list(puzzle[0]))
        new_puzzle = ([word.split(" ") for word in tok_puzzle], puzzle[1])
        return new_puzzle

    def reset_root(self, root_synset):
        self.base_puzzle_gen.reset_root(root_synset)

    def make_puzzle_matrix(self, tok_puzzles):
        '''
        concatenate first 4 tokens if exist, then merge the rest tokens 
        and append it to the end
        
        TODO: Is it possible to get rid of the topmost for-loop using torch tensor ops??
        
        '''
        matrix = []
        for tok_puzzle in tok_puzzles:
            choices, _ = tok_puzzle
            oneHotVec = []
            for choice in choices:
                choice_Vec_list = [one_hot(tok, self.vocab) for tok in choice]
                if len(choice_Vec_list) > 4:
                    choice_Vec_list[4] = [sum(vec) for vec in zip(*choice_Vec_list[4:])]
                    choice_Vec_list = choice_Vec_list[:5]
                result = [tok for word in choice_Vec_list for tok in word]
                appendix = [0] * (5*len(self.vocab) - len(result))
                oneHotVec += result + appendix 
            matrix.append(oneHotVec)
        result = cudaify(FloatTensor(matrix))
        return result 

    @staticmethod
    def from_paths(base_puzzle_gen, train_file_path, vocab_file_path):
        vocab = BpePuzzleGenerator._read_vocab(vocab_file_path)
        bpe = fastBPE.fastBPE(train_file_path, vocab_file_path)
        return BpePuzzleGenerator(base_puzzle_gen, vocab, bpe)
    
