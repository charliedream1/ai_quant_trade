# -*- coding: utf-8 -*-
# @Author   : liyi
# @Time     : 2022/12/9 22:21
# @File     : 004_寻找两个有序数组的中位数_难.py
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
https://leetcode.cn/problems/median-of-two-sorted-arrays/solution/xun-zhao-liang-ge-you-xu-shu-zu-de-zhong-wei-s-114/
   - 主要思路：要找到第 k (k>1) 小的元素，那么就取 pivot1 = nums1[k/2-1] 和 pivot2 = nums2[k/2-1] 进行比较
   - 这里的 "/" 表示整除
   - nums1 中小于等于 pivot1 的元素有 nums1[0 .. k/2-2] 共计 k/2-1 个
   - nums2 中小于等于 pivot2 的元素有 nums2[0 .. k/2-2] 共计 k/2-1 个
   - 取 pivot = min(pivot1, pivot2)，两个数组中小于等于 pivot 的元素共计不会超过 (k/2-1) + (k/2-1) <= k-2 个
   - 这样 pivot 本身最大也只能是第 k-1 小的元素
   - 如果 pivot = pivot1，那么 nums1[0 .. k/2-1] 都不可能是第 k 小的元素。把这些元素全部 "删除"，剩下的作为新的 nums1 数组
   - 如果 pivot = pivot2，那么 nums2[0 .. k/2-1] 都不可能是第 k 小的元素。把这些元素全部 "删除"，剩下的作为新的 nums2 数组
   - 由于我们 "删除" 了一些元素（这些元素都比第 k 小的元素要小），因此需要修改 k 的值，减去删除的数的个数

   复杂度分析

    时间复杂度：O(log(m+n))，其中 m 和 n 分别是数组nums1和nums2的长度。
    初始时有k=(m+n)/2 或 k=(m+n)/2+1，每一轮循环可以将查找范围减少一半，因此时间复杂度是O(log(m+n))。

    空间复杂度：O(1)。

   """

from typing import List


class Solution:
    def findMedianSortedArrays(self, nums1: List[int], nums2: List[int]) -> float:
        def get_k_item(k):
            idx1, idx2 = 0, 0  # 首地址索引

            while True:
                # 1. 终止条件
                if idx1 == nums1_len:
                    # 超过第一个数组，则从第二个数组里选取
                    return nums2[idx2 + k - 1]
                if idx2 == nums2_len:
                    # 超过第二个数组，则从第一个数组里选取
                    return nums1[idx1 + k - 1]
                if k == 1:
                    # 如果k=1，我们只要返回两个数组首元素的最小值即可
                    return min(nums1[idx1], nums2[idx2])

                # 2. 折半查找流程
                # 避免取的中位数，超过其中一个数组的边界
                new_idx1 = min(idx1 + k // 2 - 1, nums1_len - 1)
                new_idx2 = min(idx2 + k // 2 - 1, nums2_len - 1)

                # 获取中位数
                mid_val1 = nums1[new_idx1]
                mid_val2 = nums2[new_idx2]

                # 排除数组
                if mid_val1 <= mid_val2:
                    k -= new_idx1 - idx1 + 1  # 排除的数量
                    idx1 = new_idx1 + 1  # 其实位置挪到下一个位置
                else:
                    k -= new_idx2 - idx2 + 1
                    idx2 = new_idx2 + 1

        # ====== 主流程 ======
        # 中位数即2个数组合并排序后的中间的数
        # 如果总长时偶数，则是中间2个数的平均值；如果时奇数，则是中间的值
        nums1_len, nums2_len = len(nums1), len(nums2)
        total_len = (nums1_len + nums2_len)

        if total_len % 2 == 1:  # 奇数
            return get_k_item(total_len // 2 + 1)
        else:
            # 偶数时，使用中间2个数的平均值
            mid1 = get_k_item(total_len // 2)
            mid2 = get_k_item(total_len // 2 + 1)
            return (mid1 + mid2) / 2


def main():
    slu = Solution()

    # egs1:
    # 输出：2.00000
    # 解释：合并数组 = [1,2,3] ，中位数 2
    nums1 = [1, 3]
    nums2 = [2]
    ret = slu.findMedianSortedArrays(nums1, nums2)
    print(ret)

    # egs2:
    # 输出：2.50000
    # 解释：合并数组 = [1,2,3,4] ，中位数 (2 + 3) / 2 = 2.5
    nums1 = [1, 2]
    nums2 = [3, 4]
    ret = slu.findMedianSortedArrays(nums1, nums2)
    print(ret)

    # egs3:
    # 输出：4
    nums1 = [1, 3, 4, 9]
    nums2 = [1, 2, 3, 4, 5, 6, 7, 8, 9]
    ret = slu.findMedianSortedArrays(nums1, nums2)
    print(ret)


if __name__ == '__main__':
    main()
