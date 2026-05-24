/**
 * 继承层次结构 - 中间层 2
 */

import { BaseClass1 } from './Inheritance1';

export abstract class BaseClass2 extends BaseClass1 {
    intermediateMethod(): void {
        console.log('intermediate method 2');
    }
}
