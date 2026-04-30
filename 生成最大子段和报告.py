#!/usr/bin/env python3
import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.doc_generator.generator import generate_report

# 加载 profile
profile_path = '/workspace/算法设计实验/parsed/算法设计与分析实验报告模板-最新_1_profile.json'
with open(profile_path, 'r', encoding='utf-8') as f:
    profile = json.load(f)

# 创建输出目录
output_dir = '/workspace/算法设计实验/最大子段和'
os.makedirs(output_dir, exist_ok=True)

# 字段值
field_values = {
    "course_name": "算法设计与分析",
    "student_name": "学生姓名",
    "student_id": "2024001",
    "student_class": "计算机科学与技术1班",
    "experiment_name": "最大子段和问题",
    "experiment_date": "2024年12月15日",
    "experiment_location": "J13-132"
}

# 章节内容
sections = [
    {
        "title": "一、实验目的",
        "content": """1. 掌握动态规划算法的基本原理和设计思想。
2. 理解并掌握最大子段和问题的求解方法。
3. 学会使用动态规划思想分析和解决实际问题。
4. 培养算法设计和优化的能力，具备运用动态规划方法解决其他相关问题的能力。"""
    },
    {
        "title": "二、实验环境",
        "content": """操作系统：Windows 11 / Linux Ubuntu 22.04
编程语言：Python 3.10+ / C++
开发工具：Visual Studio Code / CLion
硬件环境：Intel Core i5 处理器，8GB 内存"""
    },
    {
        "title": "三、实验内容",
        "content": """给定一个整数数组，其中可能包含正数、负数和零。要求找出数组中连续子数组的最大和，即最大子段和。

示例输入：[-2, 1, -3, 4, -1, 2, 1, -5, 4]
示例输出：6
解释：连续子数组 [4, -1, 2, 1] 的和为 6，是最大的。

需要设计并实现一个高效的算法来解决这个问题，并进行测试验证。"""
    },
    {
        "title": "四、算法描述",
        "content": """本实验采用经典的 Kadane 算法（卡登算法）来求解最大子段和问题。

算法思想：
我们使用动态规划的思想，维护两个变量：
- current_max：表示以当前元素结尾的最大子段和
- global_max：表示全局的最大子段和

算法步骤：
1. 初始化 current_max 和 global_max 为数组的第一个元素
2. 从数组的第二个元素开始遍历
3. 对于每个元素，计算 current_max = max(nums[i], current_max + nums[i])
4. 如果 current_max > global_max，则更新 global_max
5. 遍历完成后，global_max 就是最大子段和

时间复杂度：O(n)，其中 n 是数组长度
空间复杂度：O(1)，只需要常数额外空间

伪代码：
function maxSubArray(nums):
    if nums is empty:
        return 0
    current_max = global_max = nums[0]
    for i from 1 to len(nums)-1:
        current_max = max(nums[i], current_max + nums[i])
        if current_max > global_max:
            global_max = current_max
    return global_max"""
    },
    {
        "title": "五、实验结果",
        "content": """测试用例1：
输入：[-2, 1, -3, 4, -1, 2, 1, -5, 4]
输出：6
解释：最大子数组为 [4, -1, 2, 1]，和为 6

测试用例2：
输入：[1, 2, 3, 4, 5]
输出：15
解释：最大子数组就是整个数组

测试用例3：
输入：[-1, -2, -3, -4, -5]
输出：-1
解释：最大子数组为 [-1]

测试用例4：
输入：[3, -1, 2, -1]
输出：4
解释：最大子数组为 [3, -1, 2]

算法执行过程分析：
以第一个测试用例为例，算法的执行过程如下：
初始化：current_max = -2, global_max = -2
i=1 (num=1): current_max = max(1, -2+1)=1, global_max=1
i=2 (num=-3): current_max = max(-3, 1-3)=-2, global_max=1
i=3 (num=4): current_max = max(4, -2+4)=4, global_max=4
i=4 (num=-1): current_max = max(-1, 4-1)=3, global_max=4
i=5 (num=2): current_max = max(2, 3+2)=5, global_max=5
i=6 (num=1): current_max = max(1, 5+1)=6, global_max=6
i=7 (num=-5): current_max = max(-5, 6-5)=1, global_max=6
i=8 (num=4): current_max = max(4, 1+4)=5, global_max=6
最终结果：6

时间复杂度分析：
算法只需要遍历数组一次，时间复杂度为 O(n)。相比暴力解法的 O(n^2)，效率大幅提升。

空间复杂度分析：
算法只使用了常数额外空间，空间复杂度为 O(1)。"""
    },
    {
        "title": "六、实验总结",
        "content": """通过本次实验，我深入理解了动态规划算法的思想和应用。最大子段和问题是一个经典的动态规划问题，Kadane 算法通过巧妙的状态设计和状态转移，将时间复杂度从 O(n^2) 优化到了 O(n)，展现了算法优化的重要性。

在实验过程中，我遇到了一些问题。首先是对边界情况的处理，当数组全部为负数时，最大子段和应该是数组中最大的那个元素，而不是 0。通过分析和调整代码，正确处理了这种情况。其次，我在理解动态规划状态转移方程时也花费了一些时间，通过手动模拟算法过程，逐渐掌握了其原理。

这次实验让我收获很大。我不仅掌握了 Kadane 算法的实现，更重要的是学会了如何用动态规划的思想去分析和解决问题。动态规划的核心在于找到合适的状态定义和状态转移方程，这需要对问题有深入的理解。在今后的学习中，我会多练习动态规划相关的题目，提高自己的算法设计和分析能力。

通过这次实验，我也认识到算法学习的重要性。一个好的算法可以极大地提高程序的效率，特别是在处理大规模数据时，高效算法的优势会更加明显。"""
    }
]

# 生成报告
template_path = '/workspace/算法设计实验/算法设计与分析实验报告模板-最新_1.docx'
output_path = '/workspace/算法设计实验/最大子段和/最大子段和实验报告.docx'

print(f"正在生成报告: {output_path}")

result = generate_report(
    template_path=template_path,
    output_path=output_path,
    profile=profile,
    field_values=field_values,
    sections=sections
)

print(f"✓ 报告生成成功: {result}")
