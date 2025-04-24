#ifndef LANDMARKS_H
#define LANDMARKS_H

#include <fstream>
#include <iostream>
#include <map>
#include <sstream>
#include <string>
#include <vector>
#include <queue>

#include "formulas.h"
#include "plans.h"
#include "problems.h"

using namespace std;

struct Edge {
    int from;
    int to;
    string type;

    friend ostream& operator<<(ostream& os, const Edge& edge) {
        return os << "Edge(from: " << edge.from << ", to: " << edge.to << ", type: " << edge.type << ")";
    };
};

struct Landmark {
    bool is_initial_state;
    bool is_goal_state;
    int landmark_layer;
    int id;
    const Formula* formula;
    vector<Edge> edges;

    Landmark() : is_initial_state(true), is_goal_state(true), landmark_layer(-1), id(-1), formula(nullptr) {}

    ~Landmark() {
        if (formula != nullptr) {
            Formula::unregister_use(formula);
        }
    }

    void set_formula(const Formula* new_formula) {
        if (formula != nullptr) {
            Formula::unregister_use(formula);
        }
        formula = new_formula;
        if (formula != nullptr) {
            Formula::register_use(formula);
        }
    }

    void set_id(int new_id) {
        this->id = new_id;
    }

    void set_landmark_layer(int new_layer) {
        this->landmark_layer = new_layer;
    }

    friend ostream& operator<<(ostream& os, const Landmark& lm) {
        lm.formula->print(os, 0, Bindings::EMPTY);
        os << "(id: " << lm.id;

        if (lm.is_initial_state) {
            os << ", Initial State";
        }
        if (lm.is_goal_state) {
            os << ", Goal State";
        }

        os << ", layer: " << lm.landmark_layer;
        os << ", edges: [" << endl;

        for (const auto& e : lm.edges) {
            os << '\t' << e << endl;
        }
        os << "] )";
        return os;
    }
};

struct LandmarkGraph {
    int num_landmarks;
    map<int, Landmark> landmarks;

    LandmarkGraph() : num_landmarks(0) {}

    friend ostream& operator<<(ostream& os, const LandmarkGraph& graph) {
        os << "LandmarkGraph(num_landmarks: " << graph.num_landmarks << ", landmarks: {" << endl;;
        for (const auto& [id, lm] : graph.landmarks) {
            os << id << ": " << lm << endl << endl;
        }
        os << "})";
        return os;
    }

    void compute_landmark_layers();
};

extern LandmarkGraph lm_graph;

void read_landmarks_file(string file_name, const Problem& problem);

#endif
