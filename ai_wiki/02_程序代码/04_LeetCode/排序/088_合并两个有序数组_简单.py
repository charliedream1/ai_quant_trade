# -*- coding: utf-8 -*-
# @Author   : liyi
# @Time     : 2022/12/19 18:34
# @File     : 088_合并两个有序数组_简单.py
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
1. 题目
题目链接：https://leetcode.cn/problems/merge-sorted-array

给你两个按 非递减顺序 排列的整数数组 nums1 和 nums2，另有两个整数 m 和 n ，分别表示 nums1 和 nums2 中的元素数目。

请你 合并 nums2 到 nums1 中，使合并后的数组同样按 非递减顺序 排列。

注意：最终，合并后数组不应由函数返回，而是存储在数组 nums1 中。为了应对这种情况，nums1 的初始长度为 m + n，
其中前 m 个元素表示应合并的元素，后 n 个元素为 0 ，应忽略。nums2 的长度为 n 。


2. 题解
题解链接：https://leetcode.cn/problems/merge-sorted-array/solution/he-bing-liang-ge-you-xu-shu-zu-by-leetco-rrb0/

复杂度分析

时间复杂度：O(m+n)。
指针移动单调递减，最多移动 m+n 次，因此时间复杂度为 O(m+n)。

空间复杂度：O(1)。
直接对数组nums1原地修改，不需要额外空间。
"""

from typing import List


class Solution:
    def merge(self, nums1: List[int], m: int, nums2: List[int], n: int) -> None:
        """
        Do not return anything, modify nums1 in-place instead.
        """
        p1 = m - 1
        p2 = n - 1
        p3 = m + n - 1
        while p1 >= 0 or p2 >= 0:
            if p1 == -1:
                nums1[p3] = nums2[p2]
                p2 -= 1
            elif p2 == -1:
                nums1[p3] = nums1[p1]
                p1 -= 1
            elif nums1[p1] > nums2[p2]:
                nums1[p3] = nums1[p1]
                p1 -= 1
            else:
                nums1[p3] = nums2[p2]
                p2 -= 1
            p3 -= 1


def main():
    slu = Solution()

    # egs1:
    # 输出：[1,2,2,3,5,6]
    # 解释：需要合并 [1,2,3] 和 [2,5,6] 。
    # 合并结果是 [1,2,2,3,5,6] ，其中斜体加粗标注的为 nums1 中的元素。
    nums1 = [1, 2, 3, 0, 0, 0]
    m = 3
    nums2 = [2, 5, 6]
    n = 3
    slu.merge(nums1, m, nums2, n)
    print('egs1:\n', nums1)

    # egs2:
    # 输出：[1]
    # 解释：需要合并[1]和[] 。
    # 合并结果是[1]
    nums1 = [1]
    m = 1
    nums2 = []
    n = 0
    slu.merge(nums1, m, nums2, n)
    print('egs2:\n', nums1)

    # egs3:
    # 输出：[1]
    # 解释：需要合并的数组是 [] 和 [1] 。 合并结果是 [1] 。
    # 注意，因为 m = 0 ，所以 nums1 中没有元素。nums1 中仅存的 0 仅仅是为了确保合并结果可以顺利存放到 nums1 中。
    nums1 = [0]
    m = 0
    nums2 = [1]
    n = 1
    slu.merge(nums1, m, nums2, n)
    print('egs3:\n', nums1)


if __name__ == '__main__':
    main()
