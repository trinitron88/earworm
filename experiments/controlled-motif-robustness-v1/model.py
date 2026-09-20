"""Unchanged PR8 observation and retrieval mechanics, with separate configurations."""
import reference_model as ref
observe=ref.observe
CAPACITY=ref.CAPACITY
NAMES=['present','recency','transition','retrieval_absolute','reference','candidate']
def forecast(history,config):
    frozen=ref.forecast(history,config['reference'])
    adapted=ref.forecast(history,config['new'])
    out={n:(frozen['retrieval_transposed'] if n=='reference' else adapted['retrieval_transposed' if n=='candidate' else n]) for n in NAMES}
    for name,value in out.items():
        source='retrieval_transposed' if name in ('reference','candidate') else name
        value['lookup_evidence']=ref.candidates(history,source,config['reference' if name=='reference' else 'new'])
    return out
