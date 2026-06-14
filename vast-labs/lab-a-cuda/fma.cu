// fma.cu — compute-bound contrast to vadd. Same data, heavy arithmetic.
// Profile both and compare SM throughput vs DRAM throughput.
#include <cstdio>
#include <cuda_runtime.h>

__global__ void fma_heavy(const float* a, const float* b, float* c, int n) {
    int i = blockIdx.x * blockDim.x + threadIdx.x;
    if (i < n) {
        float x = a[i];
        #pragma unroll
        for (int k = 0; k < 256; k++) x = x * 1.0001f + b[i];   // 256 FMAs/element
        c[i] = x;
    }
}

int main() {
    const int N = 1 << 24;
    size_t bytes = N * sizeof(float);
    float *a, *b, *c;
    cudaMallocManaged(&a, bytes);
    cudaMallocManaged(&b, bytes);
    cudaMallocManaged(&c, bytes);
    for (int i = 0; i < N; i++) { a[i] = 1.0f; b[i] = 0.0001f; }

    int threads = 256;
    int blocks = (N + threads - 1) / threads;
    fma_heavy<<<blocks, threads>>>(a, b, c, N);
    cudaDeviceSynchronize();

    printf("fma:  c[0]=%.4f (compute-bound run complete)\n", c[0]);
    cudaFree(a); cudaFree(b); cudaFree(c);
    return 0;
}
