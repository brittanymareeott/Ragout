#!/usr/bin/env python

import sys
from collections import namedtuple, defaultdict
from itertools import product


Entry = namedtuple("Entry", ["s_ref", "e_ref", "s_qry", "e_qry",
                            "len_ref", "len_qry", "ref_id", "contig_id"])

Scaffold = namedtuple("Scaffold", ["name", "contigs"])
Contig = namedtuple("Contig", ["name", "sign", "gap"])
#Hit = namedtuple("Hit", ["pos", "chr"])
class Hit:
    def __init__(self, pos, chr):
        self.pos = pos
        self.chr = chr

    def __str__(self):
        return str(self.pos) + " : " + str(self.chr)


def parse_quast_output(filename):
    entries = []
    for line in open(filename, "r"):
        line = line.strip()
        if line.startswith("[") or line.startswith("="):
            continue

        vals = line.split(" | ")
        s_ref, e_ref = map(int, vals[0].split())
        s_qry, e_qry = map(int, vals[1].split())
        len_ref, len_qry = map(int, vals[2].split())
        ref_id, contig_id = vals[4].split("\t")
        entries.append(Entry(s_ref, e_ref, s_qry, e_qry,
                            len_ref, len_qry, ref_id, contig_id))

    return entries


def parse_contigs_order(filename):
    scaffolds = []
    for line in open(filename, "r"):
        if line.startswith(">"):
            scaffolds.append(Scaffold(line.strip()[1:], []))
        else:
            name = line.strip("\n").replace("=", "_") #fix for nucmer
            without_sign = name[1:].strip()
            sign = 1 if name[0] == "+" else -1
            scaffolds[-1].contigs.append(Contig(without_sign, sign, 0))
    return scaffolds


def get_order(entries):
    MIN_HIT = 0.8

    chr_len = {}

    by_name = defaultdict(list)
    for entry in entries:
        by_name[entry.contig_id].append(entry)

    for name in by_name:
        by_name[name].sort(key=lambda e: e.len_qry, reverse=True)
        by_name[name] = filter(lambda e: e.len_qry > MIN_HIT * by_name[name][0].len_qry, by_name[name])

    filtered_entries = []
    for ent_lst in by_name.itervalues():
        filtered_entries.extend(ent_lst)

    by_chr = defaultdict(list)
    for entry in filtered_entries:
        by_chr[entry.ref_id].append(entry)
    for chr_id in by_chr:
        by_chr[chr_id].sort(key=lambda e: e.s_ref)
        chr_len[chr_id] = len(by_chr[chr_id])

    entry_ord = defaultdict(list)
    for chr_id, entries in by_chr.iteritems():
        for i, e in enumerate(entries):
            entry_ord[e.contig_id].append(Hit(i, chr_id))

    return entry_ord, chr_len


def main():
    if len(sys.argv) < 3:
        print "Usage: test.py quast_out contigs_order"
        return

    entries = parse_quast_output(sys.argv[1])
    scaffolds = parse_contigs_order(sys.argv[2])
    entry_ord, chr_len = get_order(entries)

    #TODO: check signs
    total_breaks = 0
    for s in scaffolds:
        print ">" + s.name

        prev = None
        increasing = None
        breaks = []
        for contig in s.contigs:
            if prev:
                if increasing is not None:
                    if not agreement(increasing, prev, entry_ord[contig.name], chr_len):
                        increasing = None
                        breaks.append(contig.name)
                        total_breaks += 1
                        print "$$",
                else:
                    if len(entry_ord[contig.name]) == 1 and len(prev) == 1:
                        increasing = entry_ord[contig.name][0].pos > prev[0].pos

            prev = entry_ord[contig.name]
            print contig.name, map(str, entry_ord[contig.name])
        print breaks

    print "Total breaks: ", total_breaks


def agreement(increasing, lst_1, lst_2, chr_len_dict):
    if not lst_1 or not lst_2:
        return True
    for i, j in product(lst_1, lst_2):
        same_chr = i.chr == j.chr
        if not same_chr:
            return False

        chr_len = chr_len_dict[i.chr]
        over_oric = ((increasing and i.pos > chr_len * 4 / 5 and j.pos < chr_len / 5) or
                    (not increasing and i.pos < chr_len / 5 and j.pos > chr_len * 4 / 5))

        if ((j.pos > i.pos) == increasing and abs(i.pos - j.pos) < chr_len / 3) or over_oric:
            return True
    return False


if __name__ == "__main__":
    main()