// vadd.cu — memory-bound vector add. The classic "my first kernel".
#include <cstdio>
#include <cuda_runtime.h>

__global__ void vadd(const float* a, const float* b, float* c, int n) {
    int i = blockIdx.x * blockDim.x + threadIdx.x;
    if (i < n) c[i] = a[i] + b[i];
}

int main() {
    const int N = 1 << 24;                 // 16M elements
    size_t bytes = N * sizeof(float);
    float *a, *b, *c;
    cudaMallocManaged(&a, bytes);
    cudaMallocManaged(&b, bytes);
    cudaMallocManaged(&c, bytes);
    for (int i = 0; i < N; i++) { a[i] = 1.0f; b[i] = 2.0f; }

    int threads = 256;
    int blocks = (N + threads - 1) / threads;
    vadd<<<blocks, threads>>>(a, b, c, N);
    cudaDeviceSynchronize();

    printf("vadd: c[0]=%.1f c[N-1]=%.1f (expect 3.0)\n", c[0], c[N-1]);
    cudaFree(a); cudaFree(b); cudaFree(c);
    return 0;
}
