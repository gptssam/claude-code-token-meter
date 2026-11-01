def average(nums):
    """숫자 목록의 평균을 돌려준다."""
    if not nums:
        return 0
    return sum(nums) / len(nums)
