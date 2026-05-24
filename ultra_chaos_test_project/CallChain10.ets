/**
 * 调用链文件 10
 */

import { ChainClass11 } from './CallChain11';

export class ChainClass10 {
    methodA() {
        const next = new ChainClass11();
        return next.methodB();
    }
    
    methodB() {
        return 'Chain10 B';
    }
    
    methodC() {
        this.methodA();
        this.methodB();
        return 'Chain10 C';
    }
}
