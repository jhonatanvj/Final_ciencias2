# src/bplustree.py
from dataclasses import dataclass, field
from typing import Any, List, Optional

@dataclass
class BPlusNode:
    leaf: bool
    keys: List[Any] = field(default_factory=list)
    children: List[Any] = field(default_factory=list)
    next: Optional['BPlusNode'] = None

class BPlusTree:
    def __init__(self, order: int = 32):
        if order < 3:
            raise ValueError("order must be >= 3")
        self.order = order
        self.root = BPlusNode(leaf=True)

    def _find_leaf(self, node: BPlusNode, key):
        if node.leaf:
            return node
        for i, k in enumerate(node.keys):
            if key < k:
                return self._find_leaf(node.children[i], key)
        return self._find_leaf(node.children[-1], key)

    def search(self, key):
        node = self._find_leaf(self.root, key)
        for i, k in enumerate(node.keys):
            if k == key:
                return node.children[i]
        return None

    def insert(self, key, value):
        leaf = self._find_leaf(self.root, key)
        idx = 0
        while idx < len(leaf.keys) and leaf.keys[idx] < key:
            idx += 1
        if idx < len(leaf.keys) and leaf.keys[idx] == key:
            leaf.children[idx].append(value)
            return
        leaf.keys.insert(idx, key)
        leaf.children.insert(idx, [value])
        if len(leaf.keys) > self.order - 1:
            self._split_leaf(leaf)

    def _split_leaf(self, leaf: BPlusNode):
        new_leaf = BPlusNode(leaf=True)
        mid = (len(leaf.keys) + 1) // 2
        new_leaf.keys = leaf.keys[mid:]
        new_leaf.children = leaf.children[mid:]
        leaf.keys = leaf.keys[:mid]
        leaf.children = leaf.children[:mid]
        new_leaf.next = leaf.next
        leaf.next = new_leaf
        if leaf is self.root:
            new_root = BPlusNode(leaf=False, keys=[new_leaf.keys[0]], children=[leaf, new_leaf])
            self.root = new_root
        else:
            self._insert_in_parent(self.root, leaf, new_leaf.keys[0], new_leaf)

    def _insert_in_parent(self, current, child, key, new_child):
        if current.leaf:
            return False
        for i, c in enumerate(current.children):
            if c is child:
                current.keys.insert(i, key)
                current.children.insert(i+1, new_child)
                if len(current.keys) > self.order - 1:
                    self._split_internal(current)
                return True
            if isinstance(c, BPlusNode):
                found = self._insert_in_parent(c, child, key, new_child)
                if found:
                    return True
        return False

    def _split_internal(self, node: BPlusNode):
        mid = len(node.keys) // 2
        new_node = BPlusNode(leaf=False)
        promote_key = node.keys[mid]
        new_node.keys = node.keys[mid+1:]
        new_node.children = node.children[mid+1:]
        node.keys = node.keys[:mid]
        node.children = node.children[:mid+1]
        if node is self.root:
            new_root = BPlusNode(leaf=False, keys=[promote_key], children=[node, new_node])
            self.root = new_root
        else:
            self._insert_in_parent(self.root, node, promote_key, new_node)

    def range_search(self, key_low, key_high):
        node = self._find_leaf(self.root, key_low)
        results = []
        while node:
            for i, k in enumerate(node.keys):
                if k < key_low:
                    continue
                if k > key_high:
                    return results
                results.append((k, node.children[i]))
            node = node.next
        return results

    def __repr__(self):
        node = self.root
        while not node.leaf:
            node = node.children[0]
        rows = []
        while node:
            rows.append(str(node.keys))
            node = node.next
        return "->".join(rows)
