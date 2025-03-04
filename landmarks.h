#ifndef LANDMARKS_H
#define LANDMARKS_H

#include <iostream>
#include <fstream>
#include <string>
#include <vector>
#include <map>
#include <sstream>
#include <iostream>

#include "plans.h"
#include "formulas.h"
#include "problems.h"

using namespace std;

struct Edge {
    int from;
    int to;
    string type;

    friend ostream& operator<<(ostream& os, const Edge& edge) {
        return os << "Edge(from: " << edge.from << ", to: " << edge.to << ", type: " << edge.type << ")";
    }
};

struct Landmark {
    bool is_initial_state;
    bool is_goal_state;
    int id;
    Formula* formula;
    vector<Edge> edges;

    Landmark() : is_initial_state(true), is_goal_state(true), id(-1), formula(nullptr) {}

    void set_id(int new_id) {
        this->id = new_id;
    }

    friend ostream& operator<<(ostream& os, const Landmark& lm) {
        os << "Landmark(id: " << lm.id << ", is_initial_state: " << (lm.is_initial_state ? "true" : "false") << ", is_goal_state: " << (lm.is_goal_state ? "true" : "false") << ", edges: [" << endl;
        for (size_t i = 0; i < lm.edges.size(); ++i) {
            os << '\t' <<lm.edges[i] << endl;;
        }
        os << "])";
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
};

extern LandmarkGraph lm_graph;

void read_landmarks_file(string file_name, const Problem& problem);

#endif
