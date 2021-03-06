extern "C" __declspec(dllexport) bool __stdcall meshB_inside_of_meshA(char* meshA, char* meshB);

extern "C" __declspec(dllexport) bool __stdcall convex_hull_of_mesh(char* mesh, char* hull_file);

extern "C" __declspec(dllexport) bool __stdcall simplify_mesh(char* mesh, char* simplified_mesh, float simplification_rate);