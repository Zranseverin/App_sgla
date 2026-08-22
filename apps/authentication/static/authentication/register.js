(function () {
    const form = document.querySelector("form");
    const steps = [...document.querySelectorAll("[data-registration-step]")];
    const progressItems = [...document.querySelectorAll("[data-progress-step]")];
    const previousButton = document.querySelector(".previous-step");
    const nextButton = document.querySelector(".next-step");
    const submitButton = document.querySelector(".submit-registration");

    if (!form || !steps.length) return;

    const stepWithError = steps.find((step) => step.querySelector(".error"));
    let currentStep = stepWithError
        ? Number(stepWithError.dataset.registrationStep)
        : Number(form.dataset.initialStep || 1);

    function showStep(stepNumber) {
        currentStep = Math.max(1, Math.min(stepNumber, steps.length));
        steps.forEach((step) => {
            step.hidden = Number(step.dataset.registrationStep) !== currentStep;
        });
        progressItems.forEach((item) => {
            const itemStep = Number(item.dataset.progressStep);
            item.classList.toggle("is-active", itemStep === currentStep);
            item.classList.toggle("is-complete", itemStep < currentStep);
        });
        previousButton.hidden = currentStep === 1;
        nextButton.hidden = currentStep === steps.length;
        submitButton.hidden = currentStep !== steps.length;
    }

    function validateCurrentStep() {
        const fields = [...steps[currentStep - 1].querySelectorAll("input, select, textarea")];
        const invalidField = fields.find((field) => !field.checkValidity());
        if (!invalidField) return true;
        invalidField.reportValidity();
        invalidField.focus();
        return false;
    }

    nextButton.addEventListener("click", () => {
        if (!validateCurrentStep()) return;
        showStep(currentStep + 1);
        document.querySelector(".registration-progress").scrollIntoView({ behavior: "smooth", block: "start" });
    });

    previousButton.addEventListener("click", () => {
        showStep(currentStep - 1);
        document.querySelector(".registration-progress").scrollIntoView({ behavior: "smooth", block: "start" });
    });

    showStep(currentStep);
})();
