#!/usr/bin/env python3
from __future__ import annotations
from dataclasses import dataclass
from typing import Tuple, Dict, List, Optional, Sequence, Iterable, Mapping, Any
import itertools

Token = Tuple[Tuple[int,int], ...]
Seq = Tuple[Any, ...]

def _norm_coords(cells):
    cells = tuple(sorted(set((int(r), int(c)) for r,c in cells)))
    if not cells:
        return ()
    r0=min(r for r,c in cells); c0=min(c for r,c in cells)
    return tuple(sorted((r-r0,c-c0) for r,c in cells))

def d4_canonical(cells) -> Token:
    """Translation + D4 canonicalization of a binary glyph coordinate set."""
    pts=list(cells)
    if not pts:
        return ()
    variants=[]
    for k in range(8):
        out=[]
        for r,c in pts:
            x,y=r,c
            # Four rotations, optionally reflect across vertical axis.
            rot=k%4
            for _ in range(rot):
                x,y=y,-x
            if k>=4:
                y=-y
            out.append((x,y))
        variants.append(_norm_coords(out))
    return min(variants)

@dataclass(frozen=True)
class Relation:
    mapping: Mapping[Seq, Seq]

    def segment(self, stream: Sequence[Any]) -> Optional[Tuple[Seq,...]]:
        """Return unique full segmentation into relation keys; None if 0 or >1 parses."""
        s=tuple(stream)
        keys=tuple(self.mapping.keys())
        memo={}
        def rec(i):
            if i==len(s): return [()]
            if i in memo: return memo[i]
            ans=[]
            for k in keys:
                n=len(k)
                if tuple(s[i:i+n])==tuple(k):
                    for tail in rec(i+n):
                        ans.append((tuple(k),)+tail)
                        if len(ans)>1:  # unique-or-abstain only
                            memo[i]=ans[:2]
                            return memo[i]
            memo[i]=ans
            return ans
        parses=rec(0)
        return parses[0] if len(parses)==1 else None

    def relate(self, stream: Sequence[Any]) -> Optional[Seq]:
        seg=self.segment(stream)
        if seg is None:
            return None
        out=[]
        for k in seg:
            out.extend(self.mapping[k])
        return tuple(out)

def compose(a: Relation, b: Relation) -> Optional[Relation]:
    """Compose a then b. Abstain if any a-value has non-unique b parse."""
    out={}
    for k,v in a.mapping.items():
        bv=b.relate(v)
        if bv is None:
            return None
        out[k]=bv
    return Relation(out)

def inverse_unique(rel: Relation, value: Sequence[Any]) -> Optional[Seq]:
    """Unique key whose mapped value equals requested sequence; otherwise abstain."""
    tgt=tuple(value)
    hits=[k for k,v in rel.mapping.items() if tuple(v)==tgt]
    return tuple(hits[0]) if len(hits)==1 else None

def solve_editable_relation(
    fixed: Mapping[str, Sequence[Any]],
    domains: Mapping[str, Sequence[Sequence[Any]]],
    evaluator,
    target: Sequence[Any],
) -> Optional[Dict[str, Seq]]:
    """Finite CSP inverse solve. Return assignment iff exactly one assignment satisfies target."""
    names=tuple(domains)
    sols=[]
    for choice in itertools.product(*(domains[n] for n in names)):
        asg={k:tuple(v) for k,v in fixed.items()}
        asg.update({n:tuple(v) for n,v in zip(names,choice)})
        if tuple(evaluator(asg))==tuple(target):
            sols.append({n:tuple(v) for n,v in zip(names,choice)})
            if len(sols)>1:
                return None
    return sols[0] if len(sols)==1 else None

def phase_offset(current: int, target: int, period: int, bidirectional: bool=True):
    """Return signed minimal cyclic offset, deterministic tie-break forward."""
    if period<=0: raise ValueError("period must be >0")
    f=(target-current)%period
    if not bidirectional:
        return f
    b=f-period
    if abs(b)<abs(f):
        return b
    return f

def phase_actions(delta: int, forward="ACTION1", backward="ACTION2"):
    if delta>=0:
        return (forward,)*delta
    return (backward,)*(-delta)

def plan_sites(
    current_phases: Sequence[int],
    target_phases: Sequence[int],
    period: int,
    move_right="ACTION4",
    bidirectional=True,
):
    """Cursor starts at site0; edit each site then move right to next."""
    if len(current_phases)!=len(target_phases):
        raise ValueError("length mismatch")
    actions=[]
    offsets=[]
    for i,(a,b) in enumerate(zip(current_phases,target_phases)):
        d=phase_offset(a,b,period,bidirectional)
        offsets.append(d)
        actions.extend(phase_actions(d))
        if i+1<len(current_phases):
            actions.append(move_right)
    return tuple(actions), tuple(offsets)

@dataclass(frozen=True)
class ProgramCandidate:
    name: str
    complexity: int
    predictions: Tuple[Any,...]
    evidence_ok: bool=True

def select_unique_program(candidates: Sequence[ProgramCandidate]) -> Optional[ProgramCandidate]:
    """
    Frozen selector: only evidence-consistent candidates compete.
    Choose unique minimum (complexity, prediction representation).
    If multiple candidates have equal complexity but different predictions, abstain.
    Exact duplicates collapse safely.
    """
    valid=[c for c in candidates if c.evidence_ok]
    if not valid: return None
    minc=min(c.complexity for c in valid)
    best=[c for c in valid if c.complexity==minc]
    preds={repr(c.predictions) for c in best}
    if len(preds)!=1:
        return None
    return sorted(best,key=lambda c:c.name)[0]
