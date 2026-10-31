/*
 * CartCheck 结算试算器 — practice fixture.
 *
 * This file intentionally contains exactly three seeded defects for the
 * controlled testing exercise. They are marked with "SEED-DEFECT" comments.
 * The user interface must not reveal these markers.
 */
(function () {
  "use strict";

  var amountInput = document.querySelector('input[data-testid="amount"]');
  var couponInput = document.querySelector('input[data-testid="coupon"]');
  var levelSelect = document.querySelector('select[data-testid="level"]');
  var pointsInput = document.querySelector('input[data-testid="points"]');
  var calcButton = document.querySelector('button[data-testid="calc"]');
  var discountOutput = document.querySelector('[data-testid="discount"]');
  var payableOutput = document.querySelector('[data-testid="payable"]');
  var messageOutput = document.querySelector('[data-testid="message"]');

  var AMOUNT_PATTERN = /^\d+$/;
  var AMOUNT_MIN = 1;
  var AMOUNT_MAX = 9999;
  var GOLD_THRESHOLD = 500;
  var SILVER_THRESHOLD = 800;
  var GOLD_RATE = 0.1;
  var SILVER_RATE = 0.15;

  function showResult(discount, payable, message) {
    discountOutput.textContent = discount;
    payableOutput.textContent = payable;
    messageOutput.textContent = message;
  }

  function parseAmount(raw) {
    if (!AMOUNT_PATTERN.test(raw)) {
      return null;
    }
    var value = Number(raw);
    if (!Number.isSafeInteger(value) || value < AMOUNT_MIN || value > AMOUNT_MAX) {
      return null;
    }
    return value;
  }

  function isValidCoupon(raw) {
    // SEED-DEFECT SEED-2: the "i" flag makes the coupon check case-insensitive,
    // while the requirement only accepts uppercase CP + 4 [A-Z0-9].
    return /^CP[A-Z0-9]{4}$/i.test(raw);
  }

  function calculateDiscount(amount, level) {
    if (level === "gold" && amount >= GOLD_THRESHOLD) {
      // SEED-DEFECT SEED-3: Math.round rounds half up; the requirement is floor.
      return Math.round(amount * GOLD_RATE);
    }
    // SEED-DEFECT SEED-1: ">" excludes the 800 boundary; the requirement is ">=".
    if (level === "silver" && amount > SILVER_THRESHOLD) {
      return Math.floor(amount * SILVER_RATE);
    }
    return 0;
  }

  function calculate() {
    var amount = parseAmount(amountInput.value);
    if (amount === null) {
      showResult("-", "-", "金额需为 1-9999 的整数");
      return;
    }

    if (!isValidCoupon(couponInput.value)) {
      showResult("-", "-", "优惠券码无效");
      return;
    }

    var discount = calculateDiscount(amount, levelSelect.value);
    var payable = amount - discount;

    if (pointsInput.checked) {
      payable = Math.max(0, payable - 1);
    }

    showResult(String(discount), String(payable), "");
  }

  calcButton.addEventListener("click", calculate);
})();
