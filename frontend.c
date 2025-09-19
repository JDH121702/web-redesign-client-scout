#include <Python.h>

#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static PyObject *g_analysis_module = NULL;
static PyObject *g_analysis_func = NULL;
static PyObject *g_analysis_error = NULL;

static const char *safe_utf8(PyObject *object, const char *fallback) {
    if (!object) {
        return fallback;
    }
    const char *value = PyUnicode_AsUTF8(object);
    if (!value) {
        PyErr_Clear();
        return fallback;
    }
    return value;
}

static double safe_float(PyObject *object, double fallback) {
    if (!object) {
        return fallback;
    }
    double value = PyFloat_AsDouble(object);
    if (PyErr_Occurred()) {
        PyErr_Clear();
        return fallback;
    }
    return value;
}

static long safe_long(PyObject *object, long fallback) {
    if (!object) {
        return fallback;
    }
    long value = PyLong_AsLong(object);
    if (PyErr_Occurred()) {
        PyErr_Clear();
        return fallback;
    }
    return value;
}

static bool safe_bool(PyObject *object, bool fallback) {
    if (!object) {
        return fallback;
    }
    int value = PyObject_IsTrue(object);
    if (value < 0) {
        PyErr_Clear();
        return fallback;
    }
    return value ? true : false;
}

static void trim_newline(char *buffer) {
    if (!buffer) {
        return;
    }
    size_t length = strlen(buffer);
    if (length == 0) {
        return;
    }
    if (buffer[length - 1] == '\n') {
        buffer[length - 1] = '\0';
    }
}

static bool initialize_python(void) {
    if (Py_IsInitialized()) {
        return true;
    }

    Py_Initialize();

    PyObject *sys_path = PySys_GetObject("path");
    if (sys_path && PyList_Check(sys_path)) {
        PyObject *cwd = PyUnicode_DecodeFSDefault(".");
        if (cwd) {
            if (PyList_Insert(sys_path, 0, cwd) != 0) {
                PyErr_Clear();
            }
            Py_DECREF(cwd);
        }
    }

    PyObject *module_name = PyUnicode_DecodeFSDefault("analysis_engine");
    if (!module_name) {
        PyErr_Print();
        return false;
    }

    g_analysis_module = PyImport_Import(module_name);
    Py_DECREF(module_name);
    if (!g_analysis_module) {
        PyErr_Print();
        return false;
    }

    g_analysis_func = PyObject_GetAttrString(g_analysis_module, "analyze_to_dict");
    if (!g_analysis_func || !PyCallable_Check(g_analysis_func)) {
        PyErr_Print();
        return false;
    }

    g_analysis_error = PyObject_GetAttrString(g_analysis_module, "AnalysisError");
    if (!g_analysis_error) {
        PyErr_Print();
        return false;
    }

    return true;
}

static void finalize_python(void) {
    Py_XDECREF(g_analysis_func);
    Py_XDECREF(g_analysis_module);
    Py_XDECREF(g_analysis_error);
    g_analysis_func = NULL;
    g_analysis_module = NULL;
    g_analysis_error = NULL;
    if (Py_IsInitialized()) {
        Py_Finalize();
    }
}

static void print_header(const char *title) {
    printf("\n%s\n", title);
    for (size_t i = 0; title[i] != '\0'; ++i) {
        putchar('=');
    }
    putchar('\n');
}

static void print_section(const char *title) {
    printf("\n%s\n", title);
    for (size_t i = 0; title[i] != '\0'; ++i) {
        putchar('-');
    }
    putchar('\n');
}

static void print_string_list(PyObject *list_obj, const char *label) {
    if (!list_obj || !PyList_Check(list_obj) || PyList_Size(list_obj) == 0) {
        return;
    }

    print_section(label);
    Py_ssize_t size = PyList_Size(list_obj);
    for (Py_ssize_t index = 0; index < size; ++index) {
        PyObject *item = PyList_GetItem(list_obj, index);  // Borrowed reference
        const char *text = safe_utf8(item, NULL);
        if (text) {
            printf("  - %s\n", text);
        }
    }
}

static void print_breakdown(PyObject *dict_obj) {
    if (!dict_obj || !PyDict_Check(dict_obj)) {
        return;
    }

    print_section("Design breakdown");
    PyObject *key;
    PyObject *value;
    Py_ssize_t pos = 0;
    while (PyDict_Next(dict_obj, &pos, &key, &value)) {
        const char *key_text = safe_utf8(key, NULL);
        long score = safe_long(value, 0);
        if (!key_text) {
            continue;
        }
        printf("  - %s: %ld/100\n", key_text, score);
    }
}

static bool display_analysis(const char *url) {
    if (!g_analysis_func) {
        fprintf(stderr, "Analysis function is not loaded.\n");
        return false;
    }

    PyObject *py_url = PyUnicode_FromString(url);
    if (!py_url) {
        PyErr_Print();
        return false;
    }

    PyObject *result = PyObject_CallFunctionObjArgs(g_analysis_func, py_url, NULL);
    Py_DECREF(py_url);

    if (!result) {
        if (g_analysis_error && PyErr_ExceptionMatches(g_analysis_error)) {
            PyObject *type = NULL;
            PyObject *value = NULL;
            PyObject *traceback = NULL;
            PyErr_Fetch(&type, &value, &traceback);
            PyErr_NormalizeException(&type, &value, &traceback);
            PyObject *message = value ? PyObject_Str(value) : NULL;
            const char *text = safe_utf8(message, "Unknown analysis error");
            fprintf(stderr, "Analysis error: %s\n", text ? text : "Unknown analysis error");
            Py_XDECREF(message);
            Py_XDECREF(type);
            Py_XDECREF(value);
            Py_XDECREF(traceback);
        } else {
            PyErr_Print();
        }
        return false;
    }

    if (!PyDict_Check(result)) {
        fprintf(stderr, "Unexpected result from analysis engine.\n");
        Py_DECREF(result);
        return false;
    }

    PyObject *normalized = PyDict_GetItemString(result, "normalized_url");
    PyObject *summary = PyDict_GetItemString(result, "summary");
    PyObject *design_score = PyDict_GetItemString(result, "design_score");
    PyObject *response_time = PyDict_GetItemString(result, "response_time_ms");
    PyObject *page_weight = PyDict_GetItemString(result, "page_size_kb");
    PyObject *status_code = PyDict_GetItemString(result, "status_code");
    PyObject *mobile_friendly = PyDict_GetItemString(result, "mobile_friendly");
    PyObject *last_refresh = PyDict_GetItemString(result, "last_refresh_years");
    PyObject *breakdown = PyDict_GetItemString(result, "design_breakdown");
    PyObject *strengths = PyDict_GetItemString(result, "strengths");
    PyObject *gaps = PyDict_GetItemString(result, "gaps");
    PyObject *actions = PyDict_GetItemString(result, "recommended_actions");
    PyObject *evidence = PyDict_GetItemString(result, "evidence_points");

    const char *normalized_text = safe_utf8(normalized, url);
    const char *summary_text = safe_utf8(summary, "");
    long design_value = safe_long(design_score, 0);
    double response_seconds = safe_float(response_time, 0.0) / 1000.0;
    double page_weight_kb = safe_float(page_weight, 0.0);
    long status_value = safe_long(status_code, 0);
    bool mobile = safe_bool(mobile_friendly, false);
    bool has_refresh = last_refresh && last_refresh != Py_None;
    double refresh_years = has_refresh ? safe_float(last_refresh, 0.0) : 0.0;

    print_header("Web Redesign Client Scout");
    printf("Analyzed URL: %s\n", normalized_text ? normalized_text : url);
    printf("\nSummary\n");
    printf("%s\n", summary_text ? summary_text : "No summary available.");

    print_section("Key metrics");
    printf("Design score: %ld/100\n", design_value);
    printf("Response time: %.2f seconds\n", response_seconds);
    printf("Page weight: %.0f KB\n", page_weight_kb);
    printf("HTTP status: %ld\n", status_value);
    printf("Mobile friendly: %s\n", mobile ? "Yes" : "No");
    if (has_refresh && !PyErr_Occurred()) {
        printf("Estimated last refresh: %.1f years\n", refresh_years);
    }

    print_breakdown(breakdown);
    print_string_list(strengths, "Strengths");
    print_string_list(gaps, "Gaps");
    print_string_list(actions, "Recommended actions");
    print_string_list(evidence, "Evidence points");

    PyErr_Clear();
    Py_DECREF(result);
    return true;
}

static void prompt_and_analyze(void) {
    char buffer[1024];
    printf("\nEnter the website URL: ");
    if (!fgets(buffer, sizeof buffer, stdin)) {
        return;
    }
    trim_newline(buffer);
    if (buffer[0] == '\0') {
        printf("No URL entered.\n");
        return;
    }

    if (!display_analysis(buffer)) {
        fprintf(stderr, "Analysis failed. Review the error details above.\n");
    }
}

static int read_option(void) {
    char buffer[32];
    if (!fgets(buffer, sizeof buffer, stdin)) {
        return -1;
    }
    trim_newline(buffer);
    if (buffer[0] == '\0') {
        return -1;
    }
    return buffer[0];
}

int main(void) {
    if (!initialize_python()) {
        fprintf(stderr, "Failed to initialize Python interpreter.\n");
        finalize_python();
        return EXIT_FAILURE;
    }

    bool running = true;
    while (running) {
        printf("\n==============================\n");
        printf("Web Redesign Client Scout CLI\n");
        printf("==============================\n");
        printf("1. Analyze a website\n");
        printf("2. Exit\n");
        printf("Select an option: ");

        int choice = read_option();
        switch (choice) {
            case '1':
                prompt_and_analyze();
                break;
            case '2':
                running = false;
                break;
            case -1:
                running = false;
                break;
            default:
                printf("Unknown option. Please choose 1 or 2.\n");
                break;
        }
    }

    finalize_python();
    return EXIT_SUCCESS;
}
