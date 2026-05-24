/**
 * 继承层次结构 - 中间层 4
 */

import { BaseClass3 } from './Inheritance3';

export abstract class BaseClass4 extends BaseClass3 {
    intermediateMethod(): void {
        console.log('intermediate method 4');
    }
}
