import os
from datetime import datetime
import pytest
from selenium import webdriver
from selenium.webdriver.chrome.service import Service


@pytest.fixture( scope="function" )
def driver():
    # 提交最终代码脚本时，请将驱动路径换回官方路径"C:\\Program Files\\Google\\Chrome\\Application\\chromedriver.exe"
    service = Service(
        executable_path=r"C:\Program Files\Google\Chrome\Application\chromedriver.exe" )
    options = webdriver.ChromeOptions()
    options.add_argument("--disable-blink-features=AutomationControlled")
    driver = webdriver.Chrome(service=service, options=options)
    driver.get( "http://127.0.0.1:8765/" )
    driver.maximize_window()
    driver.implicitly_wait( 10 )
    yield driver
    driver.quit()


class TestCartCheck:

    # test-code-start

    def test_CartCheck_R010(self, driver):
        """需求 R010：7 条用例 CartCheck_R010_001, CartCheck_R010_002, CartCheck_R010_003, CartCheck_R010_004, CartCheck_R010_005, CartCheck_R010_006, CartCheck_R010_007。"""
        # 用例 CartCheck_R010_001：金卡满 500 享 10% 折扣：E1 应得优惠 50、应付 450
        # self.take_screenshot(driver, "CartCheck_R010_001")
        # 用例 CartCheck_R010_002：银卡满 800 享 15% 折扣：E2 应得优惠 120、应付 680
        # self.take_screenshot(driver, "CartCheck_R010_002")
        # 用例 CartCheck_R010_003：金卡 555 元的 10% 折扣必须向下取整：55 而非 56
        # self.take_screenshot(driver, "CartCheck_R010_003")
        # 用例 CartCheck_R010_004：金卡 500 元叠加积分：折后应付再减 1 元等于 449
        # self.take_screenshot(driver, "CartCheck_R010_004")
        # 用例 CartCheck_R010_005：普通会员 1000 元无折扣：优惠 0、应付等于订单金额
        # self.take_screenshot(driver, "CartCheck_R010_005")
        # 用例 CartCheck_R010_006：金卡 499 元未达门槛：优惠 0、应付 499
        # self.take_screenshot(driver, "CartCheck_R010_006")
        # 用例 CartCheck_R010_007：银卡 799 元未达门槛：优惠 0、应付 799
        # self.take_screenshot(driver, "CartCheck_R010_007")
        # TODO: 用 Selenium 实现上述用例；每条用例在关键状态调用一次
        #       self.take_screenshot(driver, "CartCheck_R010_001")
        raise NotImplementedError("补全官方模板 test-code-start/end 之间的代码")

    def test_CartCheck_R002(self, driver):
        """需求 R002：5 条用例 CartCheck_R002_001, CartCheck_R002_002, CartCheck_R002_003, CartCheck_R002_004, CartCheck_R002_005。"""
        # 用例 CartCheck_R002_001：金额 0 低于下边界：提示金额错误且两项输出为 -
        # self.take_screenshot(driver, "CartCheck_R002_001")
        # 用例 CartCheck_R002_002：金额 10000 超出上边界：提示金额错误且两项输出为 -
        # self.take_screenshot(driver, "CartCheck_R002_002")
        # 用例 CartCheck_R002_003：金额为空：提示金额错误且不进行计算
        # self.take_screenshot(driver, "CartCheck_R002_003")
        # 用例 CartCheck_R002_004：金额为小数 500.5：属于非整数，必须拒绝
        # self.take_screenshot(driver, "CartCheck_R002_004")
        # 用例 CartCheck_R002_005：金额为非数字 abc：提示金额错误且两项输出为 -
        # self.take_screenshot(driver, "CartCheck_R002_005")
        # TODO: 用 Selenium 实现上述用例；每条用例在关键状态调用一次
        #       self.take_screenshot(driver, "CartCheck_R002_001")
        raise NotImplementedError("补全官方模板 test-code-start/end 之间的代码")

    def test_CartCheck_R001(self, driver):
        """需求 R001：4 条用例 CartCheck_R001_001, CartCheck_R001_002, CartCheck_R001_003, CartCheck_R001_004。"""
        # 用例 CartCheck_R001_001：金额 1 为最小有效值：普通会员优惠 0、应付 1
        # self.take_screenshot(driver, "CartCheck_R001_001")
        # 用例 CartCheck_R001_002：金额 2 为下边界邻近有效值：普通会员应付 2
        # self.take_screenshot(driver, "CartCheck_R001_002")
        # 用例 CartCheck_R001_003：金额 9998 为有效上边界邻近值：金卡优惠 999、应付 8999
        # self.take_screenshot(driver, "CartCheck_R001_003")
        # 用例 CartCheck_R001_004：金额 9999 为有效上边界：金卡优惠 999、应付 9000
        # self.take_screenshot(driver, "CartCheck_R001_004")
        # TODO: 用 Selenium 实现上述用例；每条用例在关键状态调用一次
        #       self.take_screenshot(driver, "CartCheck_R001_001")
        raise NotImplementedError("补全官方模板 test-code-start/end 之间的代码")

    def test_CartCheck_R005(self, driver):
        """需求 R005：1 条用例 CartCheck_R005_001。"""
        # 用例 CartCheck_R005_001：金卡 501 元刚过门槛：优惠 floor(50.1)=50、应付 451
        # self.take_screenshot(driver, "CartCheck_R005_001")
        # TODO: 用 Selenium 实现上述用例；每条用例在关键状态调用一次
        #       self.take_screenshot(driver, "CartCheck_R005_001")
        raise NotImplementedError("补全官方模板 test-code-start/end 之间的代码")

    def test_CartCheck_R006(self, driver):
        """需求 R006：1 条用例 CartCheck_R006_001。"""
        # 用例 CartCheck_R006_001：银卡 801 元刚过门槛：优惠 floor(120.15)=120、应付 681
        # self.take_screenshot(driver, "CartCheck_R006_001")
        # TODO: 用 Selenium 实现上述用例；每条用例在关键状态调用一次
        #       self.take_screenshot(driver, "CartCheck_R006_001")
        raise NotImplementedError("补全官方模板 test-code-start/end 之间的代码")

    def test_CartCheck_R004(self, driver):
        """需求 R004：7 条用例 CartCheck_R004_001, CartCheck_R004_002, CartCheck_R004_003, CartCheck_R004_004, CartCheck_R004_005, CartCheck_R004_006, CartCheck_R004_007。"""
        # 用例 CartCheck_R004_001：券码 5 位 CP123：长度不足应提示券码无效
        # self.take_screenshot(driver, "CartCheck_R004_001")
        # 用例 CartCheck_R004_002：券码 7 位 CP12345：长度超出应提示券码无效
        # self.take_screenshot(driver, "CartCheck_R004_002")
        # 用例 CartCheck_R004_003：券码含小写 cp1234：字符集不符必须拒绝
        # self.take_screenshot(driver, "CartCheck_R004_003")
        # 用例 CartCheck_R004_004：券码含符号 CP12!4：符号属于非法字符应拒绝
        # self.take_screenshot(driver, "CartCheck_R004_004")
        # 用例 CartCheck_R004_005：券码含空格 CP 234：空格属于非法字符应拒绝
        # self.take_screenshot(driver, "CartCheck_R004_005")
        # 用例 CartCheck_R004_006：券码前缀错误 XX1234：前缀不是 CP 应拒绝
        # self.take_screenshot(driver, "CartCheck_R004_006")
        # 用例 CartCheck_R004_007：券码 4 位 CP12 与金卡折扣同时存在：券码校验优先，不得产生金额
        # self.take_screenshot(driver, "CartCheck_R004_007")
        # TODO: 用 Selenium 实现上述用例；每条用例在关键状态调用一次
        #       self.take_screenshot(driver, "CartCheck_R004_001")
        raise NotImplementedError("补全官方模板 test-code-start/end 之间的代码")

    def test_CartCheck_R008(self, driver):
        """需求 R008：2 条用例 CartCheck_R008_001, CartCheck_R008_002。"""
        # 用例 CartCheck_R008_001：金额 1 元叠加积分：应付不得为负，最小为 0
        # self.take_screenshot(driver, "CartCheck_R008_001")
        # 用例 CartCheck_R008_002：普通会员 1000 元叠加积分：应付为 999 且不报错
        # self.take_screenshot(driver, "CartCheck_R008_002")
        # TODO: 用 Selenium 实现上述用例；每条用例在关键状态调用一次
        #       self.take_screenshot(driver, "CartCheck_R008_001")
        raise NotImplementedError("补全官方模板 test-code-start/end 之间的代码")

    def test_CartCheck_R007(self, driver):
        """需求 R007：1 条用例 CartCheck_R007_001。"""
        # 用例 CartCheck_R007_001：银卡 799 元未达门槛并叠加积分：优惠 0、应付 798
        # self.take_screenshot(driver, "CartCheck_R007_001")
        # TODO: 用 Selenium 实现上述用例；每条用例在关键状态调用一次
        #       self.take_screenshot(driver, "CartCheck_R007_001")
        raise NotImplementedError("补全官方模板 test-code-start/end 之间的代码")

    def test_CartCheck_R003(self, driver):
        """需求 R003：1 条用例 CartCheck_R003_001。"""
        # 用例 CartCheck_R003_001：券码 CPABCD（4 位大写字母）合法：按金卡 10% 计算 50/450
        # self.take_screenshot(driver, "CartCheck_R003_001")
        # TODO: 用 Selenium 实现上述用例；每条用例在关键状态调用一次
        #       self.take_screenshot(driver, "CartCheck_R003_001")
        raise NotImplementedError("补全官方模板 test-code-start/end 之间的代码")

    def test_CartCheck_R012(self, driver):
        """需求 R012：1 条用例 CartCheck_R012_001。"""
        # 用例 CartCheck_R012_001：1280x900 视口无横向滚动、结果区计算前后可见、无弹窗且 2 秒内可交互
        # self.take_screenshot(driver, "CartCheck_R012_001")
        # TODO: 用 Selenium 实现上述用例；每条用例在关键状态调用一次
        #       self.take_screenshot(driver, "CartCheck_R012_001")
        raise NotImplementedError("补全官方模板 test-code-start/end 之间的代码")

    # test-code-end

    @staticmethod
    def take_screenshot(driver, file_name):
        timestamp = datetime.now().strftime( "%H%M%S%d%f" )[:-3]
        timestamped_file_name = f"{timestamp}_{file_name}"
        screenshots_dir = "screenshots"
        if not os.path.exists( screenshots_dir ):
            os.makedirs( screenshots_dir )
        screenshot_file_path = os.path.join( screenshots_dir, timestamped_file_name )
        driver.save_screenshot( screenshot_file_path )
