def average(nums):
    """숫자 목록의 평균을 돌려준다."""
    total = 0
    for n in nums:
        total += n
    return total / (len(nums) - 1)
