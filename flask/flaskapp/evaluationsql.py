from flask import (
    Blueprint, request, make_response, Response, g
)
from werkzeug.exceptions import abort

from flaskapp.authsql import login_required

from typing import List

from flask_cors import cross_origin

import requests
import os
from flaskapp.dbsql import get_db

import sys
sys.path.append(os.getenv('FLASKAPP_CONTENT_DIRECTORY'))

def put_into_database(answer_list: list, endpoint: str):
    """ PUT 'answers' item into the database """
    db = get_db()

    number_of_questions = db.execute(
        'SELECT COUNT(*) FROM QUESTION'
    ).fetchone()

    if number_of_questions is None or len(answer_list) != number_of_questions:
        abort(404, 'Improper admin setup')

    enumerated_answers = list(enumerate(answer_list, start=1))
    
    try:
        account_id = g.user['AccountID']
        if account_id is None:
            raise db.IntegrityError('Invalid account ID.')
        for answer in enumerated_answers:
            db.execute(
                'INSERT INTO ANSWER (QuestionID, AccountID, AnswerText) VALUES (?, ?, ?)',
                (answer[0], account_id, answer[1],)
            )
        db.commit()
        pass
    except db.IntegrityError:
        abort(404, 'Evaluation failed.')
        pass
    pass

def censor_all_directories_in_list (list_arg: List[str]) -> List[str]:
    """
    Replaces all sensitive sections of all directories found in a list with an ellipsis (...).

    Parameters:
        list_arg (list[str]): A list of strings with potentially sensitive information

    Returns:
        A list of strings with all sensitive sections of all directories replaced with an ellipsis (...)
    """
    assert isinstance(list_arg, list), "list_arg is not a list"
    assert all(isinstance(item, str) for item in list_arg), "There is a non-string element in list_arg."
    import os
    return [item.replace(os.getenv('CENSORED_DIRECTORY_SECTION'), ' ... ') for item in list_arg]

def compute_average_overall_score(id: int) -> float:
    """
    Computes the average overall score from judge_results (rounded to
    2 decimal digits), once it no longer gets appended when necessary.

    Parameters:
        id (int): User ID

    Returns:
        the average overall score from judge_results (rounded to 2 decimal digits)
    """
    # The final sentence of each item in judge_results contains the score for its corresponding question (at least for now).
    # It follows the syntax: "SCORE FOR THIS QUESTION: <score>%".
    # Therefore to extract the score from this, slice with start_index = str.find(': ') + 2, end_index = str.find('%')
    # Round the float(score) to 2 decimal digits (as used in judge.py).
    # Take the sum of all these scores and divide it by len(judge_results) to get the average score
    score_sum: float = 0.0
    db = get_db()

    result_rows = db.execute(
        'SELECT * FROM EVALUATION_RESULT WHERE AccountID = ? ORDER BY QuestionID ASC', (id,)
    ).fetchall()
    assert result_rows, 'result_rows is None'

    judge_results = [result_row['EvalText'] for result_row in result_rows]
    assert len(judge_results) > 0, 'judge_results is None'

    for result in judge_results:
        # Extract the final sentence of result
        score_sentence: str = result[result.rfind('\n') + 1 : ]
        score_str = score_sentence[score_sentence.find(': ') + 2 : score_sentence.find('%')]
        score = round(float(score_str), 2)
        score_sum += score
    return round(score_sum / len(judge_results), 2)

def submit_average_overall_score(id: str) -> None:
    """
    Inserts to the database the pre-calculated average overall score.

    Parameters:
        id (str): User ID
    """
    db = get_db()
    overall_average = compute_average_overall_score(int(id))

    average_exists = db.execute(
        'SELECT * FROM OVERALL_AVERAGE WHERE AccountID = ?', (id,)
    ).fetchone()
    try:
        if average_exists is None:
            db.execute(
                'INSERT INTO OVERALL_AVERAGE (AccountID, Average) VALUES (?, ?)', (id, overall_average)
            )
        else:
            db.execute(
                'UPDATE OVERALL_AVERAGE SET Average = ? WHERE AccountID = ?', (overall_average, id,)
            )
        db.commit()
    except db.IntegrityError:
        abort(500, 'Evaluation failed.')
        

def launch_evaluation(id: str, answer_list: List[str]) -> None:
    """
    Launches the process of evaluating the list of the users' answers.

    Parameters:
        id (str): The user's ID
        answer_list (str): A list of answers, all of which are string values
    """
    assert isinstance(answer_list, list), 'answer_list is not a list'

    # In each 'examination_<number>' folder in 'examinations' folder, create a response.py and paste the respective code from answer_list

    for i in range(0, len(answer_list), 1):
        assert isinstance(answer_list[i], str), 'There is a non-string element in answer_list'
        try:
            with open(f'flask/flaskapp/examinations/examination_{i}/response.py', 'w') as file:
                file.write(f'# ID: {id} - Question {i}\n\n')
                file.write(answer_list[i])
        except FileNotFoundError as e: # If the parent directory does not exist
            print(f'<FileNotFoundError> examination_{i} failed: {e}')
            return

    # Run init.py in 'examinations'
    try:
        from examinations.judge_driver import run_judge
    except ModuleNotFoundError as e:
        print(f'<ModuleNotFoundError> Importing examinations.judge_driver failed: {e}')
    except ImportError as e:
        print(f'<ImportError> There is an issue with importing run_judge from examinations.judge_driver: {e}')
    else:
        for i in range(0, len(answer_list), 1):
            try:
                run_judge(f'flask\\flaskapp\\examinations\\examination_{i}')
            except Exception as e:
                print(f'<Error> judge.py is missing or unreadable in examination_{i}: {e}')
            pass

        submit_average_overall_score(id)
    pass
    
bp = Blueprint('eval', __name__, url_prefix='/eval')

@bp.route('/submit', methods=['POST'], strict_slashes=False)
@cross_origin(origins=os.getenv('FRONTEND_ENDPOINT'), supports_credentials=True) # Enables CORS
@login_required
def submit():
    if request.method == 'POST':
        id = g.user['AccountID']

        print(f"Putting {id}'s submission into the database...")
        answers : List = request.json['answers']
        print(f"{id}:\n{answers}")
        url = f"{os.getenv('SUBMISSIONS_ENDPOINT')}{id}"
        put_into_database(answers, url)
        print("Launching evaluation...")
        launch_evaluation(id = id, answer_list = answers)
        print("Completing evaluation...")
        return Response(status=200, response='The submission has been processed successfully.')
    return Response(status=403, response='Inaccessible.')
    
@bp.route('/view', methods=['GET'], strict_slashes=False)
@cross_origin(origins=os.getenv('FRONTEND_ENDPOINT'), supports_credentials=True) # Enables CORS
@login_required
def determine_viewability():
    '''
    Returns a dictionary of 2 entries indicating if the code should be viewable or not.
    Unused for now.
    '''
    if request.method == 'GET':
        id = g.user['AccountID']
        db = get_db()

        print(f'Determining viewability settings for {id}...')

        # Obtain admin_data from the SQLite database
        admin_id = 1 # This is a locally-run app, so only 1 admin is possible.
        admin_data = db.execute(
            'SELECT * FROM ADMIN_DATA WHERE AdminID = ?', (admin_id,)
        ).fetchone()

        # Obtain the user's submission data from the SQLite database
        user_info = db.execute(
            'SELECT * FROM ANSWER WHERE AccountID = ?', (id,)
        ).fetchall()

        if admin_data is None or user_info is None:
            return Response(status=500, response='Viewability undetermined')
        
        response_body = {
            # Indicates if the user has made a submission
            'submitted': True,

            # Indicates if the user's submission is to be displayed (uneditable)
            'answers_viewable': bool(admin_data['AnswersAreViewable']),

            # Indicates if the evaluation of the user's submission is to be displayed
            'evaluation_viewable': bool(admin_data['EvalsAreViewable'])
        }

        if len(user_info) <= 0:
            # If the user has not yet submitted their answers
            response_body['submitted'] = False
            response_body['answers_viewable'] = False
            response_body['evaluation_viewable'] = False
        
        print(f'Visibility settings for {id}:\n{response_body}')

        import json
        response_body_json = json.dumps(response_body) # Converts dict to JSON
        
        return Response(status=200, response=response_body_json, content_type='application/json')
    return Response(status=403, response='Inaccessible')

@bp.route('/results', methods=['GET'], strict_slashes=False)
@cross_origin(origins=os.getenv('FRONTEND_ENDPOINT'), supports_credentials=True) # Enables CORS
@login_required
def get_evaluation_results():
    if request.method == 'GET':
        id = g.user['AccountID']
        db = get_db()

        user_evals = db.execute(
            '''
            SELECT * FROM EVALUATION_RESULT
            WHERE AccountID = ?
            ORDER BY QuestionID ASC
            ''', (id,)
        ).fetchall()
        if user_evals is None:
            return Response(status=404, response='No evaluation results for this user can be found.')
        
        overall_average = db.execute(
            'SELECT * FROM OVERALL_AVERAGE WHERE AccountID = ?', (id,)
        ).fetchone()
        if overall_average is None:
            return Response(status=404, response='The overall average for this user cannot be found.')

        evaluation_text = [eval['EvalText'] for eval in user_evals]
        overall_average = overall_average['Average']
        
        evaluation_text.append(f'Your overall average score is: {overall_average}%')
        evaluation_text = censor_all_directories_in_list(evaluation_text)
        response_body = {
            'evaluation': evaluation_text
        }
        
        print(f'Evaluation_text: {evaluation_text}', type(evaluation_text), flush=True)
        import json
        response_body_json = json.dumps(response_body)
        return Response(status=200, response=response_body_json, content_type='application/json')
    return Response(status=403, response='Inaccessible')

@bp.route('/user-code', methods=['GET'], strict_slashes=False)
@cross_origin(origins=os.getenv('FRONTEND_ENDPOINT'), supports_credentials=True)
@login_required
def view_user_code():
    if request.method == 'GET':
        id = g.user['AccountID']
        db = get_db()

        user_ans = db.execute(
            '''
            SELECT * FROM ANSWER
            WHERE AccountID = ?
            ORDER BY QuestionID ASC
            ''', (id,)
        ).fetchall()
        if user_ans is None:
            return Response(status=404, response='No submissions from this user can be found.')

        submission = [answer['AnswerText'] for answer in user_ans]
        response_body = {
            'submission': submission
        }
        import json
        response_body_json = json.dumps(response_body)
        return Response(status=200, response=response_body_json, content_type='application/json')
    return Response(status=403, response='Inaccessible')


