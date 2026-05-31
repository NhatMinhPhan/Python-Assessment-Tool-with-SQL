-- The values in QUESTION should match the tutor's Python questions.
-- AdminID is set to 1 because of the locally-run nature of this app.

-- Reset ANSWER and EVALUATION_RESULTS before setting up QUESTIONS.
DELETE FROM EVALUATION_RESULT;
DELETE FROM ANSWER;
DELETE FROM QUESTION;

INSERT INTO QUESTION
    (QuestionID, Description, AdminID)
VALUES
    (0, 'Hello World', 1),
    (1, 'Double the integer', 1);