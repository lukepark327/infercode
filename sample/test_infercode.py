import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from infercode.client.infercode_client import InferCodeClient
import logging
logging.basicConfig(level=logging.INFO)

# Change from -1 to 0 to enable GPU
os.environ['CUDA_VISIBLE_DEVICES'] = "-1"

infercode = InferCodeClient(language="c")
infercode.init_from_config()
vectors = infercode.encode(["for (i = 0; i < n; i++)", "struct book{ int num; char s[27]; }shu[1000];"])

print(vectors)

