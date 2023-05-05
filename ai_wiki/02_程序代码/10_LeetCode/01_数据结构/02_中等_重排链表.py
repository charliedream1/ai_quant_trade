# -*- coding: utf-8 -*-
# @Author   : liyi
# @Time     : 2023/5/4 22:46
# @File     : 02_中等_重排链表.py
# @Project  : ai_quant_trade
# Copyright (c) Personal 2022 liyi
# Function Description: 
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


"""
题目：
 - 来源1：主站143：https://leetcode-cn.com/problems/reorder-list/
 - 来源2：https://leetcode.cn/problems/LGjMqU/

题解：
 - https://leetcode.cn/problems/LGjMqU/solution/zhong-pai-lian-biao-by-leetcode-solution-wm25/
难度：中等

=====================题目描述===============
给定一个单链表 L 的头节点 head ，单链表 L 表示为：

 L0 → L1 → … → Ln-1 → Ln 
请将其重新排列后变为：

L0 → Ln → L1 → Ln-1 → L2 → Ln-2 → …

不能只是单纯的改变节点内部的值，而是需要实际的进行节点交换。
示例 1:


输入: head = [1,2,3,4]
输出: [1,4,2,3]
示例 2:


输入: head = [1,2,3,4,5]
输出: [1,5,2,4,3]
 

提示：

链表的长度范围为 [1, 5 * 104]
1 <= node.val <= 1000
 
"""


"""
题解：
方法一：线性表
因为链表不支持下标访问，所以我们无法随机访问链表中任意位置的元素。

因此比较容易想到的一个方法是，我们利用线性表存储该链表，然后利用线性表可以下标访问的特点，直接按顺序访问指定元素，重建该链表即可。

复杂度分析

时间复杂度：O(N)，其中 N 链表中的节点数。

空间复杂度：O(N)，其中 N 是链表中的节点数。主要为线性表的开销。

作者：LeetCode-Solution
链接：https://leetcode.cn/problems/LGjMqU/solution/zhong-pai-lian-biao-by-leetcode-solution-wm25/
来源：力扣（LeetCode）
著作权归作者所有。商业转载请联系作者获得授权，非商业转载请注明出处。

"""

# Definition for singly-linked list.
class ListNode:
    def __init__(self, val=0, next=None):
        self.val = val
        self.next = next


class Solution1:
    def reorderList(self, head: ListNode) -> None:
        """
        Do not return anything, modify head in-place instead.
        """
        if not head:
            return None

        lst = []
        cur = head
        while cur:
            lst.append(cur)
            cur = cur.next

        i, j = 0, len(lst) - 1
        while i < j:
            lst[i].next = lst[j]
            i += 1

            if i == j:
                break

            lst[j].next = lst[i]
            j -= 1

        lst[i].next = None


"""
方法二：寻找链表中点 + 链表逆序 + 合并链表
注意到目标链表即为将原链表的左半端和反转后的右半端合并后的结果。

这样我们的任务即可划分为三步：

1. 找到原链表的中点（参考「876. 链表的中间结点」）。

    我们可以使用快慢指针来 O(N) 地找到链表的中间节点。

2. 将原链表的右半端反转（参考「206. 反转链表」）。

    我们可以使用迭代法实现链表的反转。

3. 将原链表的两端合并。

   因为两链表长度相差不超过1，因此直接合并即可。

作者：LeetCode-Solution
链接：https://leetcode.cn/problems/LGjMqU/solution/zhong-pai-lian-biao-by-leetcode-solution-wm25/
来源：力扣（LeetCode）
著作权归作者所有。商业转载请联系作者获得授权，非商业转载请注明出处。
"""


class Solution2:
    def reorderList(self, head: ListNode) -> None:
        if not head:
            return
        mid = self.find_mid(head)
        l2 = self.reverse_lst(mid)
        self.merge_lst(head, l2)

    def find_mid(self, head: ListNode) -> ListNode:
        fast = slow = head
        while fast.next and fast.next.next:
            fast = fast.next.next
            slow = slow.next
        return slow

    def reverse_lst(self, head: ListNode) -> ListNode:
        cur, pre = head, None
        while cur:
            cur.next, pre, cur = pre, cur, cur.next
        return pre

    def merge_lst(self, l1: ListNode, l2: ListNode):
        while l1 and l2:
            tmp_l1_nxt = l1.next
            tmp_l2_nxt = l2.next

            l1.next = l2
            l2.next = tmp_l1_nxt

            l1 = tmp_l1_nxt
            l2 = tmp_l2_nxt

