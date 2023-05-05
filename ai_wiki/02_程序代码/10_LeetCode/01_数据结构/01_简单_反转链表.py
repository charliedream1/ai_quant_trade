# -*- coding: utf-8 -*-
# @Author   : liyi
# @Time     : 2023/5/4 22:14
# @File     : 01_easy_反转链表.py
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
题目来源：
  1.剑指Offer24 https://leetcode.cn/problems/fan-zhuan-lian-biao-lcof/
  2.主站：https://leetcode-cn.com/problems/reverse-linked-list/
题解：https://leetcode.cn/problems/fan-zhuan-lian-biao-lcof/solution/jian-zhi-offer-24-fan-zhuan-lian-biao-die-dai-di-2/
难度：简单

=============== 题目============
给定单链表的头节点 head ，请反转链表，并返回反转后的链表的头节点。


示例 1：


输入：head = [1,2,3,4,5]
输出：[5,4,3,2,1]
示例 2：


输入：head = [1,2]
输出：[2,1]
示例 3：

输入：head = []
输出：[]
 

提示：

链表中节点的数目范围是 [0, 5000]
-5000 <= Node.val <= 5000
 

来源：力扣（LeetCode）
链接：https://leetcode.cn/problems/UHnkqh
著作权归领扣网络所有。商业转载请联系官方授权，非商业转载请注明出处。
"""


# Definition for singly-linked list.
class ListNode:
    def __init__(self, x):
        self.val = x
        self.next = None


class Solution:
    def reverseList(self, head: ListNode) -> ListNode:
        if not head:
            return head

        cur, pre = head, None
        while cur:
            cur.next, pre, cur = pre, cur, cur.next
        return pre
